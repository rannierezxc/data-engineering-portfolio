""" talks to the open-meteo api, retrying temporary failures with exponential backoff"""

import logging
from datetime import date
from typing import Any

import requests
from tenacity import (before_sleep_log, retry,retry_if_exception,stop_after_attempt,wait_exponential_jitter,)

from weather_pipeline.config import API_URL, HOURLY_VARIABLES, REQUEST_TIMEOUT_SECONDS, City

logger = logging.getLogger(__name__)

#temporary problems are worth retrying. But 404 or 400 means our request is wrong , so dont retry.

RETRYABLE_STATUS_CODE = {429, 500, 5092, 503, 504}

def is_retryable(exc: BaseException) -> bool:
	"""decice whether an error is temporary (retry) or permanent (give up)"""
	if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
		return True
	if isinstance(exc, requests.HTTPError) and exc.response is not None:
		return exc.response.status_code in RETRYABLE_STATUS_CODES
	return False

@retry(retry=retry_if_exception(is_retryable), stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=1, max=30), #1s,2s,4s,8s, +random jtter,
	before_sleep=before_sleep_log(logger, logging.WARNING), reraise=True,)

def fetch_raw_weather(city: City, target_date: date) -> dict[str, Any]:
	"""return the raw json as a dict of hourly weather for one city and one utc day"""
	params: dict[str, str | float] = {
		"latitude": city.latitude,
		"longitude": city.longitude,
		"hourly": ",".join(HOURLY_VARIABLES),
		"start_date": target_date.isoformat(),
		"end_date": target_date.isoformat(),
		"timezone": "UTC",
	}
	logger.info("Requesting weather for %s on %s", city.name, target_date)
	response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
	response.raise_for_status()
	payload: dict[str, Any] = response.json()
	return payload
