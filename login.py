import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import (
    logger, SEL_USERNAME_INPUT, SEL_PASSWORD_INPUT
)
from utils import human_delay, wait_for_element, take_screenshot, retry_web_action, snapshot

def get_driver(headless=False):
    """Initializes and returns a Selenium Chrome Webdriver."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Optional: Anti-bot bypass (if needed)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

@retry_web_action()
def login(driver, url, username, password):
    """Logs into the VTU internship portal. Prompts user if CAPTCHA is detected."""
    logger.info(f"Navigating to {url} for login as {username}")
    driver.get(url)
    human_delay(1.5, 3.0)
    
    # Fill username and password
    try:
        user_input = wait_for_element(driver, SEL_USERNAME_INPUT, timeout=15)
        user_input.clear()
        user_input.send_keys(username)
        human_delay(0.5, 1.2)
        
        pass_input = wait_for_element(driver, SEL_PASSWORD_INPUT, timeout=5)
        pass_input.clear()
        pass_input.send_keys(password)
        human_delay(0.5, 1.2)
        
        # Submit via locating any sign-in button
        btns = driver.find_elements(By.TAG_NAME, "button")
        clicked = False
        for b in btns:
            if "Sign In" in b.text or "Login" in b.text:
                b.click()
                clicked = True
                break
        
        if not clicked:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
        logger.info("Login form submitted.")
        human_delay(4.0, 6.0)
        snapshot(driver)
        
        # Handle 'I Understand' modal
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            if "I Understand" in b.text:
                b.click()
                logger.info("Dismissed 'I Understand' notice.")
                break
                
        human_delay(2.0, 3.0)

        # Confirm we are no longer on the login page.
        current_url = driver.current_url
        if "sign-in" in current_url or "login" in current_url:
            logger.error("Login did not complete; still on login page.")
            take_screenshot(driver, "login_failed")
            raise Exception("Login failed: invalid credentials or login flow changed.")

        logger.info("Successfully authenticated.")
        snapshot(driver)
        
    except TimeoutException as e:
        logger.error("Login process failed or dashboard not reached.")
        take_screenshot(driver, "login_failed")
        raise e

def logout(driver):
    """Safely logs out of the portal."""
    logger.info("Attempting to logout...")
    try:
        logout_btn = wait_for_element(driver, SEL_LOGOUT_BUTTON, By.CSS_SELECTOR, timeout=10)
        logout_btn.click()
        logger.info("Logout successful.")
    except Exception as e:
        logger.warning(f"Could not cleanly logout, moving on: {e}")
