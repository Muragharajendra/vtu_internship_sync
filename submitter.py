import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException

from config import (
    logger, DIARY_CREATE_URL, 
    SEL_FORM_SUMMARY, SEL_FORM_HOURS, SEL_FORM_LINKS, 
    SEL_FORM_LEARNINGS, SEL_FORM_BLOCKERS
)
from scraper import extract_entries_from_html, navigate_to_diary
from utils import wait_for_element, human_delay, take_screenshot, retry_web_action, mark_date_failed, mark_date_success, snapshot
from ai_generator import generate_diary_content

def _fill_text_input(driver, selector, text):
    try:
        ele = wait_for_element(driver, selector, By.CSS_SELECTOR, timeout=5)
        ele.clear()
        ele.send_keys(str(text))
        human_delay(0.5, 1.2)
    except TimeoutException:
        logger.warning(f"Could not find or fill text input: {selector}")
        with open('/tmp/failed_fill.html', 'w') as f:
            f.write(driver.page_source)
        raise Exception(f"Failed to find element {selector}. Dumped HTML.")

@retry_web_action()
def submit_diary_entry(driver, entry_data):
    date_str = entry_data.get('date') # Format: YYYY-MM-DD
    logger.info(f"Starting submission for date: {date_str}")
    
    try:
        driver.get(DIARY_CREATE_URL)
        human_delay(2.0, 4.0)
        snapshot(driver)
        
        # --- Form Step 1: Selection ---
        
        # 1. Select Internship
        try:
            internship_btn = wait_for_element(driver, "internship_id", By.ID, timeout=10)
            internship_btn.click()
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.DOWN).send_keys(Keys.ENTER).perform()
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Failed handling internship dropdown for {date_str}: {e}")

        # 2. Pick a Date
        try:
            date_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Pick a Date') or @data-slot='popover-trigger']")
            if date_btns:
                try:
                    date_btns[0].click()
                except Exception:
                    # Fallback to JS click if the element is intercepted by Shadcn overlays
                    driver.execute_script("arguments[0].click();", date_btns[0])
                time.sleep(1)
                
                # Navigate calendar to correct month
                target_dt = datetime.strptime(date_str, "%Y-%m-%d")
                target_month = target_dt.strftime("%B")
                
                # Loop up to 12 times to go backward
                for _ in range(12):
                    caption_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-live='polite']")
                    caption = caption_elements[0].text if caption_elements else ""
                    if target_month in caption and str(target_dt.year) in caption:
                        break
                    
                    prev_btns = (
                        driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'previous')]") or
                        driver.find_elements(By.XPATH, "//button[@name='previous-month']") or
                        driver.find_elements(By.XPATH, "//button[contains(@class, 'rdp-nav_button_previous')]")
                    )
                    if prev_btns:
                        prev_btns[0].click()
                        time.sleep(1)
                    else:
                        break

                # Click the exact day
                data_day_str = f"{target_dt.month}/{target_dt.day}/{target_dt.year}"
                
                # Month backwards navigation
                max_months_back = 12
                for _ in range(max_months_back):
                    day_btns = driver.find_elements(By.CSS_SELECTOR, f"button[data-day='{data_day_str}']")
                    if day_btns:
                        break
                    
                    prev_month_btn = driver.find_elements(By.CSS_SELECTOR, "button.rdp-button_previous, button[aria-label='Go to the Previous Month']")
                    if prev_month_btn and prev_month_btn[0].get_attribute("disabled") is None:
                        try:
                            prev_month_btn[0].click()
                        except:
                            driver.execute_script("arguments[0].click();", prev_month_btn[0])
                        time.sleep(0.8)
                    else:
                        break
                
                day_btns = driver.find_elements(By.CSS_SELECTOR, f"button[data-day='{data_day_str}']")
                if day_btns:
                    try:
                        # ActionChains simulates real mouse events required by Shadcn UI
                        ActionChains(driver).move_to_element(day_btns[-1]).click().perform()
                    except:
                        driver.execute_script("arguments[0].click();", day_btns[-1])
                    time.sleep(1)
                else:
                    logger.warning(f"Could not find day button for {date_str}!")
        except Exception as e:
            logger.warning(f"Failed handling calendar for {date_str}: {e}")
            raise Exception("Calendar picker blocked progress.")

        # 3. Hit Continue
        con_btn = wait_for_element(driver, "//button[text()='Continue']", By.XPATH, timeout=5)
        
        # Close the calendar popover explicitly by dispatching ESC
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        try:
            con_btn.click()
        except:
            try:
                # If intercept occurs, force it 
                driver.execute_script("arguments[0].click();", con_btn)
            except:
                pass # Stale references mean success (DOM changed)
        human_delay(3.0, 5.0)
        snapshot(driver)

        # --- Form Step 2: Details ---
        
        work_summary = entry_data.get('work_summary', '').strip()
        learnings = entry_data.get('learnings', '').strip()
        hours_worked = entry_data.get('hours_worked', 8.0)
        
        if not work_summary:
            ai_content = generate_diary_content(date_str, hours_worked)
            work_summary = ai_content['work_summary']
            learnings = ai_content['learnings']

        # Ensure bounds
        work_summary = work_summary[:2000]
        learnings = learnings[:2000]

        _fill_text_input(driver, SEL_FORM_SUMMARY, work_summary)
        _fill_text_input(driver, SEL_FORM_HOURS, str(hours_worked))
        _fill_text_input(driver, SEL_FORM_LEARNINGS, learnings)
        _fill_text_input(driver, SEL_FORM_BLOCKERS, "None")
        _fill_text_input(driver, SEL_FORM_LINKS, "")

        # Try to select a generic skill from react select
        try:
            skills_inputs = driver.find_elements(By.CSS_SELECTOR, "input[id^='react-select-']")
            if skills_inputs:
                skills_inputs[0].click()
                time.sleep(1)
                ActionChains(driver).send_keys(Keys.DOWN).send_keys(Keys.ENTER).perform()
                time.sleep(1)
        except:
            pass
            
        snapshot(driver)
        # Hit Save
        try:
            save_btns = driver.find_elements(By.XPATH, "//button[text()='Save' or text()='Submit']")
            if not save_btns:
                raise Exception("Could not find Save/Submit button")

            try:
                save_btns[0].click()
            except:
                driver.execute_script("arguments[0].click();", save_btns[0])
        except Exception as e:
            logger.error(f"Save button error: {e}")
            raise

        human_delay(4.0, 6.0)

        # --- VERIFY submission (check that the entry shows updated summary) ---
        try:
            navigate_to_diary(driver)
            page_entries = extract_entries_from_html(driver.page_source)
            matching = [e for e in page_entries if e.get('date') == date_str]
            if matching:
                current_summary = matching[0].get('work_summary', '').strip()
                intended_summary = work_summary.strip()
                if intended_summary and intended_summary not in current_summary:
                    raise Exception(f"Submitted summary did not persist (expected: {intended_summary[:30]}..., got: {current_summary[:30]}...)" )
            else:
                raise Exception(f"No diary entry found for {date_str} after submission")

            logger.info(f"Successfully submitted entry for {date_str}.")
            mark_date_success(date_str)
        except Exception as e:
            logger.error(f"Verification failed after submit for {date_str}: {e}")
            take_screenshot(driver, prefix=f"submit_verify_{date_str}")
            with open("/tmp/failed_step2.html", "w") as f:
                f.write(driver.page_source)
            mark_date_failed(date_str)
            raise

    except Exception as e:
        logger.error(f"Failed submission for {date_str}: {e}")
        take_screenshot(driver, prefix=f"submit_{date_str}")
        with open("/tmp/failed_step2.html", "w") as f:
            f.write(driver.page_source)
        mark_date_failed(date_str)
        raise
