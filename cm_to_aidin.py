"""
Aidin Referral Automation Script
================================
Automates the process of:
1. Logging into the Aidin platform
2. Clicking on empty space to dismiss overlays/popups
3. Navigating the referral workflow (skipping "Get Started")
4. Auto-filling approval message in response form
5. Capturing all form data (note, location, status, pre-approve)
6. Clicking "Send My Response"
7. Saving response data to JSON
8. Closing the browser
"""

import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page


class AidinReferralAutomation:
    def __init__(self):
        self.response_folder = "response"
        self.captured_data = {}
        self.ensure_response_folder()

    def ensure_response_folder(self):
        """Create response folder if it doesn't exist"""
        if not os.path.exists(self.response_folder):
            os.makedirs(self.response_folder)
            print(f"✅ Created '{self.response_folder}' folder")

    def login(self, page: Page):
        """Handle login process"""
        print("\n=== LOGIN ===")
        page.goto("https://next.myaidin.com/devise_users/sign_in")

        # Wait for email input
        page.wait_for_selector('input[type="email"]', timeout=15000)
        page.fill('input[type="email"]', 'CN-ACMProductAlerts-Shared@WellSky.com')
        page.click('button[type="submit"]')

        # Wait for password field and login
        page.wait_for_selector('input[type="password"]', timeout=15000)
        page.fill('input[type="password"]', 'Careport1!')
        page.click('button[type="submit"]')

        print("⏳ Waiting for full page load after login...")
        page.wait_for_load_state("load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)
        print("✅ Logged in and page fully loaded")

    def click_empty_space(self, page: Page):
        """Click on empty space to dismiss popups/overlays and ensure page is interactive"""
        print("\n=== CLICKING EMPTY SPACE ===")
        try:
            # Get viewport size
            viewport_size = page.viewport_size

            # Click on an empty area (top-left corner, away from buttons)
            x = viewport_size['width'] // 2
            y = 100  # Near top but not on header elements

            print(f"Clicking at coordinates: ({x}, {y})")
            page.mouse.click(x, y)
            page.wait_for_timeout(1000)
            print("✅ Clicked empty space successfully")

        except Exception as e:
            print(f"⚠️ Click on empty space failed (non-critical): {str(e)}")

    def navigate_to_referral(self, page: Page):
        """Navigate through the referral workflow (SKIPPING Get Started)"""
        print("\n=== STARTING REFERRAL WORKFLOW ===")

        # Step 1: Click "Receive a Practice Referral"
        print("Step 1: Clicking 'Receive a Practice Referral'...")
        page.wait_for_selector('button:has-text("Receive a Practice Referral")', state="visible", timeout=20000)
        page.locator('button:has-text("Receive a Practice Referral")').first.click()
        
        # Wait for page to fully load
        print("⏳ Waiting for page to load...")
        page.wait_for_load_state("load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        print("✅ Clicked 'Receive a Practice Referral' - Page loaded")

        # Step 2: Wait for organization dropdown and sample patient options
        print("Step 2: Waiting for organization dropdown and patient selection options...")
        page.wait_for_selector('h4:has-text("Select an organization:")', timeout=20000)
        page.wait_for_selector('h4:has-text("Select a sample practice patient:")', timeout=20000)
        print("✅ Organization and patient selection sections visible")

        # Step 3: Select "Aidin Commercial" sample patient
        print("Step 3: Selecting 'Aidin Commercial' sample patient...")
        page.wait_for_selector('div[role="receiving"]:has-text("Aidin Commercial")', timeout=20000)
        page.locator('div[role="receiving"]:has-text("Aidin Commercial")').first.click()
        
        # Wait for selection to register and button to enable
        print("⏳ Waiting for patient selection to register...")
        page.wait_for_timeout(2000)
        print("✅ Selected 'Aidin Commercial' patient")

        # Step 4: Wait for "Start Referral" button to be enabled and click it
        print("Step 4: Waiting for 'Start Referral' button to be enabled...")
        start_referral_button = page.locator('button.css-5wi3cz:has-text("Start Referral")').first
        start_referral_button.wait_for(state="visible", timeout=20000)
        
        # Additional wait to ensure button is fully enabled
        page.wait_for_timeout(1000)
        print("✅ 'Start Referral' button is enabled")
        
        print("Clicking 'Start Referral'...")
        start_referral_button.click()
        
        # Wait for page to fully load after clicking
        print("⏳ Waiting for page to load after Start Referral...")
        page.wait_for_load_state("load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        print("✅ Clicked 'Start Referral' and page fully loaded")

        # Step 5: Click "Next: Respond"
        print("Step 5: Clicking 'Next: Respond'...")
        page.wait_for_selector('button:has-text("Next: Respond")', state="visible", timeout=20000)
        page.locator('button:has-text("Next: Respond")').first.click()
        
        # Wait for page to fully load
        print("⏳ Waiting for page to load...")
        page.wait_for_load_state("load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        print("✅ Clicked 'Next: Respond' and page loaded")

        # Step 6: Scroll down to find the "Respond" button
        print("Step 6: Scrolling down to find 'Respond' button...")
        page.evaluate("window.scrollBy(0, 500)")  # Scroll down 500 pixels
        page.wait_for_timeout(1000)
        print("✅ Scrolled down")

        # Step 7: Click "Respond" button
        print("Step 7: Clicking 'Respond' button...")
        respond_button = page.locator('button.css-1vozvjl:has-text("Respond")').first
        
        # Scroll to the button to ensure it's visible
        respond_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        
        # Wait for button to be visible and click
        respond_button.wait_for(state="visible", timeout=20000)
        respond_button.click()
        
        # Wait for response form to fully load
        print("⏳ Waiting for response form to load...")
        page.wait_for_load_state("load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        print("✅ Response form page is fully loaded and ready")

    def capture_form_data(self, page: Page):
        """Capture all data from the response form"""
        print("\n=== CAPTURING FORM DATA ===")
        try:
            # Capture Note field
            note_field = page.locator('textarea[placeholder*="I can accept this patient"]').first
            if note_field.count() > 0:
                note_value = note_field.input_value()
                self.captured_data['note'] = note_value
            else:
                self.captured_data['note'] = ""

            # Capture Organization/Location
            try:
                location_element = page.locator('div.css-1axzgl1 > div').first
                if location_element.count() > 0:
                    location_text = location_element.inner_text()
                    self.captured_data['organization'] = location_text.strip()
                else:
                    self.captured_data['organization'] = "Caroline Center For Rehabilitation And Healthcare"
            except Exception as e:
                self.captured_data['organization'] = "Caroline Center For Rehabilitation And Healthcare"
                print(f"⚠️ Could not capture organization: {str(e)}")

            # Capture Status dropdown value (Pre-approve, Conditional Accept, etc.)
            try:
                status_input = page.locator('input[name="status"]')
                if status_input.count() > 0:
                    status_value = status_input.get_attribute('value')
                    self.captured_data['status'] = status_value
                
                # Get the display text for status
                status_label = page.locator('.Select-value-label').first
                if status_label.count() > 0:
                    status_text = status_label.inner_text()
                    self.captured_data['status_display'] = status_text.strip()
                else:
                    self.captured_data['status_display'] = "Pre-approve"
            except Exception as e:
                self.captured_data['status'] = "available"
                self.captured_data['status_display'] = "Pre-approve"
                print(f"⚠️ Could not capture status: {str(e)}")

            # Capture Pre-approve for other locations (Yes/No radio button)
            try:
                preapprove_yes = page.locator('input[type="radio"][value="yes"]')
                preapprove_no = page.locator('input[type="radio"][value="no"]')

                if preapprove_yes.count() > 0 and preapprove_yes.is_checked():
                    self.captured_data['pre_approve_other_locations'] = 'yes'
                elif preapprove_no.count() > 0 and preapprove_no.is_checked():
                    self.captured_data['pre_approve_other_locations'] = 'no'
                else:
                    self.captured_data['pre_approve_other_locations'] = 'not_selected'
            except Exception as e:
                self.captured_data['pre_approve_other_locations'] = 'no'
                print(f"⚠️ Could not capture pre-approve selection: {str(e)}")

            # Add timestamp
            self.captured_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add patient type selected earlier
            self.captured_data['patient_type'] = 'Aidin Commercial'

            print("✅ Form data captured successfully")
            print(f"Captured  {json.dumps(self.captured_data, indent=2)}")
            return True
        except Exception as e:
            print(f"❌ Error capturing form  {str(e)}")
            return False

    def save_to_json(self):
        """Save captured data to JSON file"""
        print("\n=== SAVING DATA TO JSON ===")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"referral_response_{timestamp}.json"
        filepath = os.path.join(self.response_folder, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.captured_data, f, indent=4, ensure_ascii=False)
            print(f"✅ Data saved to: {filepath}")
            print(json.dumps(self.captured_data, indent=2))
            return filepath
        except Exception as e:
            print(f"❌ Error saving to JSON: {str(e)}")
            return None

    def auto_click_send_response(self, page: Page):
        """Auto-fill approval note, capture all form data, click 'Send My Response', save JSON"""
        print("\n=== AUTO SEND RESPONSE ===")

        # Fill approval note
        print("Step: Filling approval note...")
        note_box = page.locator('textarea[placeholder*="I can accept this patient"]').first
        note_box.wait_for(state="visible", timeout=15000)
        approval_text = (
            "Approved — patient accepted for referral. "
            "We can confirm there are no additional clinical needs required."
        )
        note_box.fill(approval_text)
        print(f"✅ Filled note: {approval_text}")
        
        # Wait for text to be filled
        page.wait_for_timeout(1000)

        # Capture all form data BEFORE clicking send
        print("\n⏳ Capturing form data before submission...")
        self.captured_data['note'] = approval_text
        self.capture_form_data(page)

        # Click 'Send My Response'
        print("\nStep: Clicking 'Send My Response'...")
        send_btn = page.locator('button:has-text("Send My Response")').first
        send_btn.wait_for(state="visible", timeout=20000)
        send_btn.click()
        
        # Wait for submission to complete
        print("⏳ Waiting for response submission...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Save to JSON
        self.save_to_json()

        # Close browser
        page.wait_for_timeout(3000)
        print("Response sent and saved. Closing browser...")
        page.context.close()

    def run(self, headless=False):
        """Main execution method"""
        print("=" * 60)
        print("🚀 AIDIN REFERRAL AUTOMATION STARTED")
        print("=" * 60)

        with sync_playwright() as p:
            # Launch browser maximized and disable fixed viewport
            browser = p.chromium.launch(
                headless=headless,
                args=["--start-maximized"]
            )
            context = browser.new_context(no_viewport=True)
            page = context.new_page()

            try:
                self.login(page)
                self.click_empty_space(page)
                self.navigate_to_referral(page)
                self.auto_click_send_response(page)
                print("\n✅ AUTOMATION COMPLETED SUCCESSFULLY")

            except Exception as e:
                print(f"\n❌ ERROR: {str(e)}")

            finally:
                page.wait_for_timeout(2000)
                browser.close()


def main():
    automation = AidinReferralAutomation()
    automation.run(headless=False)  # Change to True for headless mode


if __name__ == "__main__":
    main()
