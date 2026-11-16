import csv
import json
from datetime import date

import pytest

from weather_pipeline.main import dates_to_process, parse_args
from weather_pipeline.models import WeatherResponse
from weather_pipeline.storage import save_raw_json, save_readings_csv
from weather_pipeline.transform import to_readings


def test_backfill_range_includes_both_ends():
    args = parse_args(["--start", "2026-10-30", "--end", "2026-11-02"])
    assert dates_to_process(args) == [
        date(2026, 10, 30),
        date(2026, 10, 31),
        date(2026, 11, 1),
        date(2026, 11, 2),
    ]


def test_start_after_end_is_an_error():
    args = parse_args(["--start", "2026-11-05", "--end", "2026-11-01"])
    with pytest.raises(SystemExit):
        dates_to_process(args)


def test_single_date():
    assert dates_to_process(parse_args(["--date", "2026-11-10"])) == [date(2026, 11, 10)]


def test_raw_json_is_saved_in_date_folder(tmp_path, manila, sample_payload):
    path = save_raw_json(sample_payload, manila, date(2026, 11, 10), base_dir=tmp_path)
    assert path == tmp_path / "date=2026-11-10" / "manila.json"
    assert json.loads(path.read_text()) == sample_payload


def test_csv_has_header_and_rows(tmp_path, manila, sample_payload):
    readings = to_readings(manila, WeatherResponse.model_validate(sample_payload))
    path = save_readings_csv(readings, date(2026, 11, 10), base_dir=tmp_path)

    with path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert rows[0]["city"] == "Manila"

    assert rows[2]["temperature_c"] == ""  # None is written as an empty cell


#  tmp_path is a built-in pytest fixture giving each test a fresh temporary folder, which is deleted afterwards. Tests never touch your real data/ folder.
