import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

JSON_DATA_PATH = DATA_DIR / "internship_diary.json"
CSV_DATA_PATH = DATA_DIR / "internship_diary.csv"
CHECKPOINT_PATH = DATA_DIR / "checkpoint.json"

# Credentials
ACCOUNT1_USER = os.getenv("ACCOUNT1_USER")
ACCOUNT1_PASS = os.getenv("ACCOUNT1_PASS")
ACCOUNT2_USER = os.getenv("ACCOUNT2_USER")
ACCOUNT2_PASS = os.getenv("ACCOUNT2_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# URL setup
LOGIN_URL_A1 = "https://vtu.internyet.in/sign-in"
LOGIN_URL_A2 = "https://vtu.internyet.in/sign-in"
DIARY_CREATE_URL = "https://vtu.internyet.in/dashboard/student/student-diary"
DIARY_VIEW_URL = "https://vtu.internyet.in/dashboard/student/diary-entries"

# Sync behavior
# When True, the sync will attempt to submit entries even if the date already exists in Account-1.
# This helps overwrite/refresh existing diary entries rather than only adding missing dates.
SYNC_OVERWRITE = os.getenv("SYNC_OVERWRITE", "true").lower() in ("1", "true", "yes")

# Generic / Login Selectors
SEL_USERNAME_INPUT = "input[placeholder='Enter your email address']"
SEL_PASSWORD_INPUT = "input#password"

# Account 2: Scraper Selectors (View Diary Page)
SEL_DIARY_ROW = "table tbody tr"

# Account-1 Creation Form Selectors
SEL_FORM_SUMMARY = "textarea[name='description']"
SEL_FORM_HOURS = "input[type='number']"
SEL_FORM_LINKS = "textarea[name='links']"
SEL_FORM_LEARNINGS = "textarea[name='learnings']"
SEL_FORM_BLOCKERS = "textarea[name='blockers']"

def setup_logger():
    logger = logging.getLogger("VTUSync")
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(LOGS_DIR / "sync.log")
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger

logger = setup_logger()
