import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add parent directory to path so we can import the original scripts
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from api import models
from datetime import datetime
import asyncio
import traceback
import base64

def start_sync_background(job_id: int, req: dict, db: Session):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return
        
    # Inject dynamic credentials into the config module namespace so sync_engine picks them up
    import config
    config.ACCOUNT1_USER = req.get("dest_email")
    config.ACCOUNT1_PASS = req.get("dest_password")
    config.ACCOUNT2_USER = req.get("source_email")
    config.ACCOUNT2_PASS = req.get("source_password")
    config.CURRENT_JOB_ID = job_id
        
    job.status = "running"
    job.logs += f"[{datetime.utcnow().isoformat()}] Started background sync job. Filter Date: {req.get('start_date')}\n"
    job.logs += f"[{datetime.utcnow().isoformat()}] Source Account: {config.ACCOUNT2_USER}\n"
    job.logs += f"[{datetime.utcnow().isoformat()}] Target Account: {config.ACCOUNT1_USER}\n"
    db.commit()

    try:
        from sync_engine import run_sync
        from config import logger
        
        # We need a way to capture the logger output or adapt the script
        # For simplicity in this demo, we'll run it and just capture completion.
        # In a real setup, we'd pipe the logs back to the DB or websocket.
        
        # Set up a custom logger handler to pipe to DB
        import logging
        class DBPipeHandler(logging.Handler):
            def emit(self, record):
                log_msg = self.format(record)
                # Re-fetch job to avoid stale session
                current_job = db.query(models.Job).filter(models.Job.id == job_id).first()
                if current_job:
                    current_job.logs += f"[{datetime.utcnow().isoformat()}] {log_msg}\n"
                    db.commit()

        db_handler = DBPipeHandler()
        logger.addHandler(db_handler)
        
        job.logs += f"[{datetime.utcnow().isoformat()}] Calling sync_engine.run_sync() in headless mode with UI streaming...\n"
        db.commit()
        
        run_sync(headless=True, dry_run=False, resume=False, start_date_filter=req.get("start_date", "2026-02-03"))
        
        logger.removeHandler(db_handler)
        
        job.status = "completed"
        job.logs += f"[{datetime.utcnow().isoformat()}] Sync completed successfully.\n"
        
        # Deduct entry
        user = db.query(models.User).filter(models.User.id == job.user_id).first()
        if user and user.entries_remaining > 0:
            user.entries_remaining -= 1 # Or subtract based on how many it actually syncs
            
    except Exception as e:
        job.status = "failed"
        job.logs += f"[{datetime.utcnow().isoformat()}] Error: {str(e)}\n"
        job.logs += traceback.format_exc()
    
    db.commit()
