import json
from pathlib import Path
from typing import Any


class VirtualMemoryStore:
    def __init__(self, storage_dir: str = "data_store"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: Any) -> None:
        """Save data as JSON if it is serializable."""
        path = self.storage_dir / f"{key}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, key: str, default=None) -> Any:
        path = self.storage_dir / f"{key}.json"
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
