import logging
import os

def setup_logger(log_file: str):
    logger = logging.getLogger("sanic_server")
    logger.setLevel(logging.DEBUG)

    # Ensure the log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
