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

logging.basicConfig(level=logging.INFO)
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
    
    
    async def extract_raw_text_from_aidin(self, opportunity_data) -> str:
        """Extract raw text for opportunity data."""
        async with async_playwright() as playwright:
            chromium = playwright.chromium # or "firefox" or "webkit".
            base_download_path = os.path.join(os.getcwd(), "patient_downloads")
            os.makedirs(base_download_path, exist_ok=True)
            temp_download_path = os.path.join(os.getcwd(), "temp_downloads")
            os.makedirs(temp_download_path, exist_ok=True)
            patient_num = 1  # For demo, using a static patient number
            patient_folder = os.path.join(base_download_path, f"patient_{patient_num}")
            os.makedirs(patient_folder, exist_ok=True)
            browser = await chromium.launch(headless=True)
            logger.debug("Browser launched")
            context = await browser.new_context(
                accept_downloads=True,
                no_viewport=True
            )
            page = await context.new_page()
            logger.debug("New page created")

            await page.goto('https://next.myaidin.com/devise_users/sign_in')
            logger.info("Navigated to login page")

            await page.get_by_role('textbox').fill('CN-ACMProductAlerts-Shared@WellSky.com')
            logger.info("Filled email")

            await page.get_by_role('button', name='Submit').click()
            logger.info("Clicked submit button")

            await page.locator('input[name="password"]').click()
            logger.info("Clicked password field")

            await page.locator('input[name="password"]').fill('Careport1!')
            logger.info("Filled password")

            await page.get_by_role('button', name='Log In').click()
            logger.info("Clicked login button")

            await page.wait_for_timeout(10000)
            logger.info("Waited for page load")

            await page.locator('#dashboard-main-panel > div.panel-item-0 >> div.panel-item-0 >> div.panel-item-0 >> div.mp-eye').nth(0).click()
            logger.info("Clicked dashboard panel eye icon")

            await page.wait_for_timeout(10000)
            logger.info("Waited for content load")
            
            quick_view_data = await page.locator('div#quickview').text_content()
            logger.info(f'Quick View Data: {quick_view_data}')

            patient_info = await page.locator("div#face-sheet").text_content()
            logger.info(f'Patient Info: {patient_info}')

            insurance_data = await page.locator("div#insurance").text_content()
            logger.info(f'Insurance Data: {insurance_data}')
            
             # EXTRACT ATTACHMENT NAMES FROM DOM
            logger.info("📄 Extracting attachment names from DOM...")
            attachment_names = []

            try:
                attachment_items = page.locator('div.css-rpbvww.eyg1w0i0')
                attachment_count_dom = await attachment_items.count()
                logger.info(f"   Found {attachment_count_dom} attachment items in DOM")
                for i in range(attachment_count_dom):
                    logger.info(f"   Processing attachment item {i+1}...")
                    try:
                        span = attachment_items.nth(i).locator('span.css-nzo6od.eyg1w0i1')
                        if await span.count() > 0:
                            name = await span.inner_text()
                            logger.info(f"     Raw attachment name: {name}")
                            safe_name = self.sanitize_filename(name)
                            attachment_names.append(safe_name)
                            logger.info(f"   - Found: {safe_name}")
                    except:
                        attachment_names.append(f"attachment_{i+1}")
                
                if len(attachment_names) == 0:
                    logger.info("   ⚠️  No attachment names found, using defaults")
                    attachment_names = [f"attachment_{i+1}" for i in range(5)]
                
            except Exception as e:
                logger.info(f"   ⚠️  Could not extract names: {e}")
                attachment_names = [f"attachment_{i+1}" for i in range(5)]

            logger.info("✅ Clicking 'Select all'...")
            await page.locator('div.css-wucv12.e1d434dc2:has-text("Select all")').click()
            await page.wait_for_timeout(1000)

            logger.info("📎 Clicking 'Send X Attachments'...")
            send_btn = page.locator('div.css-axf28c.e15t2fki5[color="#fc2e5c"]')
            send_btn_text = await send_btn.inner_text()
            
            match = re.search(r'(\d+)', send_btn_text)
            attachment_count = int(match.group(1)) if match else 0
            logger.info(f"📊 Attachment count: {attachment_count}")
            
            await send_btn.click()
            await page.wait_for_timeout(1500)
            
            logger.info("⬇️  Clicking 'Download' option...")
            await page.locator('div[data-testid="menu_download"]:has-text("Download")').click()
            await page.wait_for_timeout(2000)
            
            # HANDLE BASED ON ATTACHMENT COUNT
            if attachment_count == 1:
                # FOR 1 FILE: Opens in new tab
                logger.info("📄 Single file - clicking 'Download PDF' (opens in new tab)...")
                
                try:
                    # Use the first attachment name
                    pdf_filename = f"{attachment_names[0]}.pdf" if attachment_names else f"patient_{patient_num}.pdf"
                    
                    with context.expect_page() as new_page_info:
                        download_pdf_btn = page.locator('div[color="#3c4277"].css-axf28c.e15t2fki5:has-text("Download PDF")')
                        
                        if await download_pdf_btn.count() > 0:
                            await download_pdf_btn.click()
                        else:
                            await page.locator('div.css-axf28c.e15t2fki5:has-text("Download PDF")').first.click()
                    
                    pdf_page = new_page_info.value
                    logger.info("   PDF opened in new tab, waiting for load...")
                    await pdf_page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    pdf_url = pdf_page.url
                    logger.info(f"   PDF URL: {pdf_url}")
                    
                    logger.info(f"   Downloading PDF as: {pdf_filename}")
                    response = await pdf_page.goto(pdf_url)
                    pdf_content = await response.body()
                    
                    pdf_path = os.path.join(patient_folder, pdf_filename)
                    
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    logger.info(f"✅ Saved: {pdf_filename}")
                    
                    await pdf_page.close()
                    logger.info("   Closed PDF tab")
                    await page.bring_to_front()
                    
                except Exception as e:
                    logger.info(f"❌ Single file download failed: {e}")
                    for pg in context.pages:
                        if pg != page:
                            try:
                                await pg.close()
                            except:
                                pass
                
            elif attachment_count > 1:
                # FOR MULTIPLE FILES: Download zip and extract with proper names
                logger.info(f"📦 Multiple files ({attachment_count}) - clicking 'Download Separately'...")
                
                try:
                    download_separately_btn = page.locator('div.css-axf28c.e15t2fki5:has-text("Download Separately")')
                    
                    if await download_separately_btn.count() > 0:
                        await download_separately_btn.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000)
                        
                        logger.info("📥 Clicking 'Download files'...")
                        async with page.expect_download(timeout=30000) as download_info:
                            download_files_btn = page.locator('button:has-text("Download files"), button:has-text("Download Files")')
                            await download_files_btn.first.click()
                        
                        download = await download_info.value
                        temp_zip = os.path.join(temp_download_path, f"p{patient_num}_{download.suggested_filename}")
                        await download.save_as(temp_zip)
                        logger.info(f"✅ Downloaded zip: {download.suggested_filename}")
                        await page.wait_for_timeout(2000)
                        
                        logger.info("📂 Extracting and renaming files...")
                        try:
                            with zipfile.ZipFile(temp_zip, 'r') as zf:
                                file_list = zf.namelist()
                                logger.info(f"   Found {len(file_list)} files in zip")
                                
                                # Extract and rename files based on attachment names
                                for idx, zip_file in enumerate(file_list):
                                    # Extract to temp location
                                    zf.extract(zip_file, temp_download_path)
                                    temp_file_path = os.path.join(temp_download_path, zip_file)
                                    
                                    # Determine new filename
                                    if idx < len(attachment_names):
                                        # Get extension from original file
                                        _, ext = os.path.splitext(zip_file)
                                        if not ext:
                                            ext = '.pdf'
                                        new_filename = f"{attachment_names[idx]}{ext}"
                                    else:
                                        new_filename = os.path.basename(zip_file)
                                    
                                    # Move to patient folder with new name
                                    new_file_path = os.path.join(patient_folder, new_filename)
                                    os.rename(temp_file_path, new_file_path)
                                    logger.info(f"   ✓ {new_filename}")
                                
                            os.remove(temp_zip)
                            logger.info(f"✅ Extracted and renamed {len(file_list)} files")
                            
                        except Exception as e:
                            logger.info(f"❌ Zip Extract error: {e}")
                    else:
                        logger.info("⚠️  'Download Separately' button not found")
                        
                except Exception as e:
                    logger.info(f"❌ Multiple file download failed: {e}")
            else:
                logger.info("⚠️  No files to download")
            
            files = os.listdir(patient_folder) if os.path.exists(patient_folder) else []
            logger.info(f"✅ Total files in folder: {len(files)}")
            for f in files:
                logger.info(f"   - {f}")
            
            await browser.close()
            logger.info("Browser closed")
            return {"quick_view_data": quick_view_data, "patient_info": patient_info, "insurance_data": insurance_data}
    
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
        prompt = f"Extract the quick view, patient and insurance information from following raw text and transform it into JSON format: \n\n{raw_text}"
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

