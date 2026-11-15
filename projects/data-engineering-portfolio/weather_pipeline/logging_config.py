""" logging setup: send every log line to the screen and to logs/pipeline.log"""

import logging
from logging.handlers import RotatingFileHandler

from weather_pipeline.config import LOG_DIR

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

def setup_logging(level: int = logging.INFO) -> None:
	root = logging.getLogger()
	if root.handlers: #already configured (ex: called twice) then do nothing
		return

	LOG_DIR.mkdir(parents=True, exist_ok=True)
	formatter = logging.Formatter(LOG_FORMAT)
	
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	
	file_handler = RotatingFileHandler(LOG_DIR / "pipeline.log", maxBytes=5_000_000, #start a new file after 5MB
			backupCount=3, #keep pipeline.log.1 ... pipeline.log.3
			encoding="utf-8",
	)
	
	file_handler.setFormatter(formatter)
	
	root.setLevel(level)
	root.addHandler(console_handler)
	root.addHandler(file_handler)

