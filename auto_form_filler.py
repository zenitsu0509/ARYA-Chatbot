#!/usr/bin/env python3
"""
Optional browser automation helper for complaint form filling
This script can be used to automatically fill the complaint form
Requires selenium and a web driver
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

logger = logging.getLogger(__name__)

class ComplaintFormFiller:
    def __init__(self, headless=False):
        """Initialize the browser automation."""
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome driver with options."""
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return False
    
    def fill_complaint_form(self, complaint_data):
        """
        Fill the complaint form automatically.
        
        complaint_data should contain:
        {
            'email': 'user@example.com',
            'name': 'User Name',
            'phone': '9876543210',
            'room': 'A-101',
            'category': 'Electrical',
            'description': 'Issue description',
            'summary': 'Brief summary'
        }
        """
        if not self.driver:
            if not self.setup_driver():
                return False
        
        try:
            # Navigate to the complaint portal
            self.driver.get("https://grs.ietlucknow.ac.in/open.php")
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Fill email field
            self._fill_field_by_name("email", complaint_data.get('email', ''))
            
            # Fill name field
            self._fill_field_by_name("name", complaint_data.get('name', ''))
            self._fill_field_by_name("fullname", complaint_data.get('name', ''))
            
            # Fill phone fields
            self._fill_field_by_name("phone", complaint_data.get('phone', ''))
            self._fill_field_by_name("mobile", complaint_data.get('phone', ''))
            
            # Fill problem summary
            summary = f"Room {complaint_data.get('room', '')} - {complaint_data.get('summary', '')}"
            self._fill_field_by_name("summary", summary)
            self._fill_field_by_name("subject", summary)
            
            # Fill description/message
            self._fill_field_by_name("message", complaint_data.get('description', ''))
            self._fill_field_by_name("issue", complaint_data.get('description', ''))
            
            # Fill location
            location = f"Room {complaint_data.get('room', '')}"
            self._fill_field_by_name("location", location)
            
            # Try to select help topic if available
            self._select_help_topic()
            
            print("✅ Form filled successfully!")
            print("📝 Please review the form, complete any remaining fields (like CAPTCHA), and submit manually.")
            
            # Keep browser open for user to review and submit
            input("Press Enter after you've submitted the form to close the browser...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def _fill_field_by_name(self, field_name, value):
        """Fill a form field by name."""
        try:
            # Try different selectors
            selectors = [
                f"input[name='{field_name}']",
                f"textarea[name='{field_name}']",
                f"#{field_name}",
                f".{field_name}"
            ]
            
            for selector in selectors:
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    field.clear()
                    field.send_keys(value)
                    logger.info(f"Filled {field_name} with {value}")
                    return True
                except NoSuchElementException:
                    continue
            
            logger.warning(f"Could not find field: {field_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error filling field {field_name}: {e}")
            return False
    
    def _select_help_topic(self):
        """Try to select an appropriate help topic."""
        try:
            # Look for help topic dropdown
            help_topic_selectors = [
                "select[name='topicId']",
                "select[name='topic']",
                "select[name='help_topic']",
                "#topicId"
            ]
            
            for selector in help_topic_selectors:
                try:
                    select_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    select = Select(select_element)
                    
                    # Try to select a relevant option
                    options_text = [option.text.lower() for option in select.options]
                    
                    # Look for relevant categories
                    preferred_options = ['cwn', 'internet', 'wifi', 'infrastructure', 'general']
                    
                    for pref in preferred_options:
                        for i, option_text in enumerate(options_text):
                            if pref in option_text:
                                select.select_by_index(i)
                                logger.info(f"Selected help topic: {select.options[i].text}")
                                return True
                    
                    # If no preferred option found, select the first non-empty option
                    if len(select.options) > 1:
                        select.select_by_index(1)
                        logger.info(f"Selected default help topic: {select.options[1].text}")
                        return True
                        
                except NoSuchElementException:
                    continue
            
            logger.warning("Could not find help topic dropdown")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting help topic: {e}")
            return False

# Example usage
if __name__ == "__main__":
    # Example complaint data
    sample_data = {
        'email': 'john.doe@ietlucknow.ac.in',
        'name': 'John Doe',
        'phone': '9876543210',
        'room': 'A-101',
        'category': 'Electrical',
        'description': 'The ceiling fan in my room is not working. It was working fine yesterday but today it completely stopped. I have checked the switch and it seems to be fine.',
        'summary': 'Room fan not working'
    }
    
    # Note: This requires selenium and chromedriver to be installed
    print("🤖 Automated Form Filler")
    print("📋 This will open a browser and try to fill the complaint form automatically.")
    print("⚠️  Note: You'll still need to complete the CAPTCHA and submit manually.")
    
    response = input("Do you want to proceed? (y/n): ")
    if response.lower() == 'y':
        filler = ComplaintFormFiller(headless=False)
        filler.fill_complaint_form(sample_data)
    else:
        print("Cancelled.")
