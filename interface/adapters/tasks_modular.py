import os
import re
import zipfile
from ui_workflow_agent.agent import root_agent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
from datetime import datetime
from typing import AsyncIterator, Optional
from domain.messages import AgentResponse, AidinExtractedData
from playwright.async_api import async_playwright, Playwright
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TaskAdapter:
    def sanitize_filename(self, filename):
        """Remove invalid characters from filename and replace pipe with hyphen"""
        # Replace pipe with hyphen
        filename = filename.replace('|', '-')
        # Remove invalid filesystem characters
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        # Trim whitespace
        filename = filename.strip()
        return filename
    
    
    async def _setup_browser(self, playwright: Playwright):
        """Setup browser and create necessary directories"""
        logger.info("Setting up browser and directories...")
        chromium = playwright.chromium
        base_download_path = os.path.join(os.getcwd(), "patient_downloads")
        temp_download_path = os.path.join(os.getcwd(), "temp_downloads")
        patient_folder = os.path.join(base_download_path, f"patient_1")  # Using static patient number
        
        for path in [base_download_path, temp_download_path, patient_folder]:
            os.makedirs(path, exist_ok=True)
            
        browser = await chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True, no_viewport=True)
        page = await context.new_page()
        
        return browser, context, page, patient_folder, temp_download_path

    async def _login_to_aidin(self, page):
        """Handle login process"""
        logger.info("Logging into AIDIN...")
        await page.goto('https://next.myaidin.com/devise_users/sign_in')
        await page.get_by_role('textbox').fill('CN-ACMProductAlerts-Shared@WellSky.com')
        await page.get_by_role('button', name='Submit').click()
        await page.locator('input[name="password"]').click()
        await page.locator('input[name="password"]').fill('Careport1!')
        await page.get_by_role('button', name='Log In').click()
        await page.wait_for_timeout(10000)

    async def _extract_patient_data(self, page):
        """Extract patient and insurance information"""
        await page.locator('#dashboard-main-panel > div.panel-item-0 >> div.panel-item-0 >> div.panel-item-0 >> div.mp-eye').nth(0).click()
        await page.wait_for_timeout(10000)
        
        patient_info = await page.locator("div#face-sheet").text_content()
        insurance_data = await page.locator("div#insurance").text_content()
        
        return patient_info, insurance_data

    async def _get_attachment_names(self, page):
        """Extract attachment names from the page"""
        attachment_names = []
        try:
            attachment_items = page.locator('div.css-rpbvww.eyg1w0i0')
            attachment_count_dom = await attachment_items.count()
            
            for i in range(attachment_count_dom):
                span = attachment_items.nth(i).locator('span.css-nzo6od.eyg1w0i1')
                if await span.count() > 0:
                    name = await span.inner_text()
                    safe_name = self.sanitize_filename(name)
                    attachment_names.append(safe_name)
                    
        except Exception as e:
            logger.info(f"Could not extract names: {e}")
            
        return attachment_names or [f"attachment_{i+1}" for i in range(5)]

    async def _handle_single_file_download(self, context, page, patient_folder, attachment_names):
        """Handle downloading of a single file"""
        try:
            pdf_filename = f"{attachment_names[0]}.pdf" if attachment_names else "patient_1.pdf"
            
            with context.expect_page() as new_page_info:
                download_pdf_btn = page.locator('div[color="#3c4277"].css-axf28c.e15t2fki5:has-text("Download PDF")')
                await (download_pdf_btn if await download_pdf_btn.count() > 0 
                      else page.locator('div.css-axf28c.e15t2fki5:has-text("Download PDF")').first).click()
            
            pdf_page = new_page_info.value
            await pdf_page.wait_for_load_state("networkidle", timeout=30000)
            response = await pdf_page.goto(pdf_page.url)
            pdf_content = await response.body()
            
            with open(os.path.join(patient_folder, pdf_filename), 'wb') as f:
                f.write(pdf_content)
            
            await pdf_page.close()
            await page.bring_to_front()
            
        except Exception as e:
            logger.info(f"Single file download failed: {e}")
            for pg in context.pages:
                if pg != page:
                    await pg.close()

    async def _handle_multiple_files_download(self, page, patient_folder, temp_download_path, attachment_names):
        """Handle downloading of multiple files"""
        try:
            logger.info("Handling multiple file download...")
            download_separately_btn = page.locator('div.css-axf28c.e15t2fki5:has-text("Download Separately")')
            if await download_separately_btn.count() > 0:
                await download_separately_btn.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)            
            logger.info("📥 Clicking 'Download files'...")
            
            async with page.expect_download(timeout=30000) as download_info:
                await page.locator('button:has-text("Download files"), button:has-text("Download Files")').first.click()
            
            download = await download_info.value
            temp_zip = os.path.join(temp_download_path, f"p1_{download.suggested_filename}")
            await download.save_as(temp_zip)
            logger.info(f"Downloaded zip to {temp_zip}")
            
            await self._extract_and_rename_files(temp_zip, temp_download_path, patient_folder, attachment_names)
            os.remove(temp_zip)
        except Exception as e:
            logger.error(f"Multiple file download failed: {e}")
            raise

    async def _extract_and_rename_files(self, temp_zip, temp_download_path, patient_folder, attachment_names):
        """Extract and rename files from zip"""
        with zipfile.ZipFile(temp_zip, 'r') as zf:
            for idx, zip_file in enumerate(zf.namelist()):
                logger.info(f"Extracting {zip_file}...")
                zf.extract(zip_file, temp_download_path)
                temp_file_path = os.path.join(temp_download_path, zip_file)
                
                if idx < len(attachment_names):
                    _, ext = os.path.splitext(zip_file)
                    ext = ext or '.pdf'
                    new_filename = f"{attachment_names[idx]}{ext}"
                else:
                    new_filename = os.path.basename(zip_file)
                
                new_file_path = os.path.join(patient_folder, new_filename)
                os.rename(temp_file_path, new_file_path)
                logger.info(f"Renamed and moved to {new_file_path}")

    async def extract_raw_text_from_aidin(self, opportunity_data) -> str:
        """Extract raw text for opportunity data."""
        async with async_playwright() as playwright:
            browser, context, page, patient_folder, temp_download_path = await self._setup_browser(playwright)
            logger.info("Browser and directories set up successfully.")
            await self._login_to_aidin(page)
            logger.info("Logged into AIDIN successfully.")
            patient_info, insurance_data = await self._extract_patient_data(page)
            logger.info("Extracted patient and insurance data successfully.")
            attachment_names = await self._get_attachment_names(page)
            logger.info(f"Attachment names extracted: {attachment_names}")
            
            await page.locator('div.css-wucv12.e1d434dc2:has-text("Select all")').click()
            logger.info("Selected all attachments.")
            send_btn = page.locator('div.css-axf28c.e15t2fki5[color="#fc2e5c"]')
            attachment_count = int(re.search(r'(\d+)', await send_btn.inner_text()).group(1) or 0)
            
            await send_btn.click()
            logger.info("Clicked send button for attachments.")
            await page.locator('div[data-testid="menu_download"]:has-text("Download")').click()
            logger.info(f"Number of attachments to download: {attachment_count}")
            if attachment_count == 1:
                await self._handle_single_file_download(context, page, patient_folder, attachment_names)
            elif attachment_count > 1:
                await self._handle_multiple_files_download(page, patient_folder, temp_download_path, attachment_names)
            
            await browser.close()
            return {"patient_info": patient_info, "insurance_data": insurance_data}
    
    async def transform_raw_text_to_json(self, raw_text: str) -> dict:
        """
            Creates FHIR formatted data from raw text by using ADK agent
        """
        APP_NAME = "aidin_fhir_transformer"
        USER_ID = "user_123"
        session_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        # Session and Runner
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        prompt = f"Extract the patient and insurance information from following raw text and transform it into JSON format: \n\n{raw_text}"
        logger.info(f'Prompt for data extraction: {prompt}')
        content = types.Content(role='user', parts=[types.Part(text=prompt)])
        try:
            events = runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content)
            final_response_text = await self._async_extract_final_response_text(events)
        except Exception as e:
            logger.info(f"Error during agent response processing: {e}")
            return AgentResponse(
                userId=USER_ID,
                message="Some error in your request. Please try again later.",
                sessionId=session_id
            )

        logger.info(f'Final extracted JSON: {final_response_text}')
        final_agent_response = AgentResponse(
            userId=USER_ID,
            message=final_response_text,
            sessionId=session_id
        )
        return final_response_text
        
    # Helper function to extract the final response text from ADK events [Temp fix for Bug: https://github.com/comet-ml/opik/issues/2467#issuecomment-2970768612]
    async def _async_extract_final_response_text(self, events: AsyncIterator[Event]) -> Optional[str]:
        """
        Exhausts the async iterator of ADK events and returns the response text
        from the last event (presumably the final root agent response).
        """
        collected_events = []

        # This `async for` loop iterates through the `events` iterator.
        async for event in events:
            collected_events.append(event)
            
        if not collected_events:
            raise Exception("Agent failed to execute: No events received.")

        last_event: Event = collected_events[-1]
        
        # This code only runs AFTER the `async for` loop above has completed and all events have been collected.
        # The last event should be the final response from the root agent.
        if last_event.is_final_response():
            if last_event.content and last_event.content.parts:
                return last_event.content.parts[0].text
            elif last_event.actions and last_event.actions.escalate: # Handle potential errors/escalations
                return f"Agent escalated: {last_event.error_message or 'No specific message.'}"
            else:
                return "No final response text found."
        
        logger.info(f"Last event was not a final response. Event: {last_event}")
        raise Exception("Agent did not produce a final response.")

