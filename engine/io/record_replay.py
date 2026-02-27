from pathlib import Path
import json
from typing import Iterator

RECORDINGS_DIR = Path("data/recordings")

def load_recording(provider: str) -> Iterator[dict]:
    """
    Open data/recordings/{provider}_raw.jsonl, parse each line as JSON, yield dict.
    """
    file_path = RECORDINGS_DIR / f"{provider}_raw.jsonl"
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def replay_stream(provider: str):
    """
    Yield entry["raw"] for each line in the provider's recording.
    """
    for entry in load_recording(provider):
        yield entry["raw"]
