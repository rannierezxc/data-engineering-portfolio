import json
from pathlib import Path

from ingest import save_json


def test_save_json_writes_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "weather.json"
    save_json({"temperature": 30.5}, target)

    assert target.exists()
    assert json.loads(target.read_text()) == {"temperature": 30.5}
