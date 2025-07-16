import logging

def setup_logger(log_file="logs/app.log", log_level=logging.INFO):
    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger()
    return logger
