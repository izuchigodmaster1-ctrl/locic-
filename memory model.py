import json
from pathlib import Path
from typing import Any


def save_to_memory(data: Any, storage_file: str = "data_store/memory.json") -> None:
    """Saves data to a JSON file."""
    path = Path(storage_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_from_memory(storage_file: str = "data_store/memory.json") -> Any:
    """Loads data from a JSON file."""
    path = Path(storage_file)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)