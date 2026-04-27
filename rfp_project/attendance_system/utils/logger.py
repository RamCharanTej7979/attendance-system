import logging
import os

def setup_logger():
    """
    Sets up a basic console and file logger for the application.
    """
    logger = logging.getLogger("AttendanceSystem")
    logger.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # File handler
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.log")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # Add handlers
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger

app_logger = setup_logger()
