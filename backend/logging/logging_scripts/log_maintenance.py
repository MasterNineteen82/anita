import os
import shutil
import glob
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('log_maintenance')

# Configuration
LOG_DIR = Path("k:/anita/poc/logs")
ARCHIVE_DIR = LOG_DIR / "archive"
MAX_LOG_AGE_DAYS = 30
MAX_ARCHIVED_MONTHS = 6  # Keep archived logs for 6 months

def setup_directories():
    """Ensure all required directories exist"""
    LOG_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    (LOG_DIR / "active").mkdir(exist_ok=True)

def archive_old_logs():
    """Archive logs older than MAX_LOG_AGE_DAYS"""
    today = datetime.now()
    cutoff_date = today - timedelta(days=MAX_LOG_AGE_DAYS)
    current_month_dir = ARCHIVE_DIR / today.strftime("%Y-%m")
    current_month_dir.mkdir(exist_ok=True)
    
    # Find old app logs
    app_logs = LOG_DIR.glob("app_*.log")
    archived_count = 0
    
    for log_file in app_logs:
        # Extract date from filename (format: app_YYYYMMDD_HHMMSS.log)
        try:
            file_date_str = log_file.name.split("_")[1]
            file_date = datetime.strptime(file_date_str, "%Y%m%d")
            
            if file_date < cutoff_date:
                # Archive the file
                target_path = current_month_dir / log_file.name
                shutil.move(str(log_file), str(target_path))
                archived_count += 1
        except (IndexError, ValueError) as e:
            logger.warning(f"Could not parse date from filename {log_file.name}: {e}")
    
    logger.info(f"Archived {archived_count} log files to {current_month_dir}")

def rotate_error_log():
    """Rotate the errors.log file weekly"""
    error_log = LOG_DIR / "errors.log"
    if not error_log.exists():
        return
    
    # Get file size in MB
    size_mb = error_log.stat().st_size / (1024 * 1024)
    
    # If file is larger than 10MB or it's Sunday, rotate it
    if size_mb > 10 or datetime.now().weekday() == 6:
        timestamp = datetime.now().strftime("%Y%m%d")
        target_path = LOG_DIR / f"errors_{timestamp}.log"
        shutil.copy(str(error_log), str(target_path))
        
        # Clear the original file
        with open(error_log, 'w') as f:
            f.write(f"# Rotated on {datetime.now().isoformat()}\n")
        
        logger.info(f"Rotated error log to {target_path}")

def cleanup_old_archives():
    """Remove archive folders older than MAX_ARCHIVED_MONTHS"""
    today = datetime.now()
    cutoff_month = today.replace(day=1) - timedelta(days=1)
    cutoff_month = cutoff_month.replace(day=1)
    
    for _ in range(MAX_ARCHIVED_MONTHS):
        cutoff_month = cutoff_month.replace(day=1) - timedelta(days=1)
        cutoff_month = cutoff_month.replace(day=1)
    
    cutoff_str = cutoff_month.strftime("%Y-%m")
    
    # Find all month directories
    month_dirs = [d for d in ARCHIVE_DIR.iterdir() if d.is_dir() and d.name <= cutoff_str]
    
    for old_dir in month_dirs:
        logger.info(f"Removing old archive: {old_dir}")
        shutil.rmtree(old_dir)

def main():
    """Run all log maintenance tasks"""
    setup_directories()
    archive_old_logs()
    rotate_error_log()
    cleanup_old_archives()
    logger.info("Log maintenance completed successfully")

if __name__ == "__main__":
    main()