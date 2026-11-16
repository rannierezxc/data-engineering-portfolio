"""
tests the network code without the network.
the 'responses' library fakes the api

"""

from datetime import date

import pytest
import requests
import responses
from tenacity import wait_none

from weather_pipeline.client import fetch_raw_weather
from weather_pipeline.config import API_URL

TARGET_DATE = date(2026, 11, 10)

# same function, but without the real sleep between retries, so tests stay fast
fast_fetch = fetch_raw_weather.retry_with(wait=wait_none())


@responses.activate
def test_success_returns_json(manila, sample_payload):
    responses.add(responses.GET, API_URL, json=sample_payload, status=200)

    result = fast_fetch(manila, TARGET_DATE)

    assert result["hourly"]["time"][0] == "2026-11-10T00:00"
    sent_url = responses.calls[0].request.url
    assert "start_date=2026-11-10" in sent_url
    assert "timezone=UTC" in sent_url


@responses.activate
def test_retries_on_server_error_then_succeeds(manila, sample_payload):
    responses.add(responses.GET, API_URL, status=503)
    responses.add(responses.GET, API_URL, status=503)
    responses.add(responses.GET, API_URL, json=sample_payload, status=200)

    result = fast_fetch(manila, TARGET_DATE)

    assert len(responses.calls) == 3  # failed twice, succeedd on the 3rd try
    assert result["latitude"] == 14.6


@responses.activate
def test_gives_up_after_five_attempts(manila):
    responses.add(responses.GET, API_URL, status=500)

    with pytest.raises(requests.HTTPError):
        fast_fetch(manila, TARGET_DATE)
    assert len(responses.calls) == 5


@responses.activate
def test_does_not_retry_client_errors(manila):
    responses.add(responses.GET, API_URL, status=400)

    with pytest.raises(requests.HTTPError):
        fast_fetch(manila, TARGET_DATE)
    assert len(responses.calls) == 1  # 400 = our fault, retrying wont help


#      @responses.activate intercepts every requests call inside the test and returns the fake responses you registered, in order. Thats how we simulate 503 503 and 200.

#      retry_with(wait=wait_none()) makes a copy of our function with no waiting, so the retry tests take milliseconds isntead of 30 secs
