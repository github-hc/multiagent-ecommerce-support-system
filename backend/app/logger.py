import os
import logging
from logging.handlers import RotatingFileHandler

# Directory for logs inside the container/volume
LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

# Ensure the logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Standard logging format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
formatter = logging.Formatter(LOG_FORMAT)

# Configure Root Logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear existing handlers to prevent duplicate logs
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Console Stream Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

# Rotating File Handler
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# App Logger instance
logger = logging.getLogger("backend")
logger.info(f"Observability logging initialized. Output file: {LOG_FILE}")
