import time
from datetime import datetime
from config import logger
from scraper import scrape_account_entries
from submitter import submit_diary_entry
from login import login, logout, get_driver
from utils import get_failed_entries_from_checkpoint

def filter_by_date(entries, cutoff_date="2026-02-03"):
    """
    Returns only entries situated on or after the cutoff date.
    Assumes entries have 'date' in YYYY-MM-DD format.
    """
    filtered = []
    cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")
    for e in entries:
        try:
            entry_dt = datetime.strptime(e['date'], "%Y-%m-%d")
            if entry_dt >= cutoff:
                filtered.append(e)
        except Exception as exc:
            logger.warning(f"Could not parse date {e['date']} for filtering: {exc}")
    return filtered

def compute_missing_entries(entries_a2, entries_a1, overwrite=False):
    """Compute which entries should be submitted.

    If `overwrite` is False (default), only dates missing from Account-1 are returned.
    If `overwrite` is True, all entries from Account-2 will be returned (after date filtering), allowing the script to overwrite existing records.
    """
    dates_a1 = {entry['date'] for entry in entries_a1}

    if overwrite:
        entries_to_sync = list(entries_a2)
        logger.info("Overwrite enabled: will submit all entries from source (Account-2) regardless of existing dates in target.")
    else:
        entries_to_sync = [entry for entry in entries_a2 if entry['date'] not in dates_a1]

    logger.info(f"Total entries in source (A2): {len(entries_a2)}")
    logger.info(f"Total entries in target (A1): {len(entries_a1)}")
    logger.info(f"Entries to sync: {len(entries_to_sync)}")

    # Sort chronologically (oldest first)
    entries_to_sync.sort(key=lambda x: x['date'])
    return entries_to_sync

def run_sync(headless=False, dry_run=False, resume=False, start_date_filter="2026-02-03"):
    from config import ACCOUNT1_USER, ACCOUNT1_PASS, ACCOUNT2_USER, ACCOUNT2_PASS, LOGIN_URL_A1, LOGIN_URL_A2, SYNC_OVERWRITE
    overwrite_config = SYNC_OVERWRITE

    if not all([ACCOUNT1_USER, ACCOUNT1_PASS, ACCOUNT2_USER, ACCOUNT2_PASS]):
        logger.error("Missing credentials in .env. Exiting.")
        return

    logger.info("=== STEP 1: Scraping Source (Account-2) ===")
    driver_a2 = get_driver(headless=headless)
    try:
        login(driver_a2, LOGIN_URL_A2, ACCOUNT2_USER, ACCOUNT2_PASS)
        entries_a2 = scrape_account_entries(driver_a2, save_to_disk=True)
    finally:
        driver_a2.quit()
        time.sleep(2)

    logger.info("=== STEP 2: Scraping Target (Account-1) ===")
    driver_a1 = get_driver(headless=headless)
    try:
        login(driver_a1, LOGIN_URL_A1, ACCOUNT1_USER, ACCOUNT1_PASS)
        entries_a1 = scrape_account_entries(driver_a1, save_to_disk=False)

        entries_a2_filtered = filter_by_date(entries_a2, cutoff_date=start_date_filter)
        missing_entries = compute_missing_entries(entries_a2_filtered, entries_a1, overwrite_config)

        if resume:
            failed_dates = get_failed_entries_from_checkpoint()
            if failed_dates:
                logger.info(f"Resuming only for failed dates: {failed_dates}")
                missing_entries = [e for e in missing_entries if e['date'] in failed_dates]

        logger.info("=== STEP 3: Submitting Missing Entries ===")
        if dry_run:
            logger.info("DRY RUN MODE ENABLED. The following will NOT be submitted:")
            for e in missing_entries:
                logger.info(f" - [{e['date']}] {e['work_summary'][:50]}...")
        else:
            for entry in missing_entries:
                submit_diary_entry(driver_a1, entry)
                
    finally:
        driver_a1.quit()
        
    logger.info("=== SYNC COMPLETE ===")
