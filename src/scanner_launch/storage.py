from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scanner_launch.config import settings
from scanner_launch.models import to_dict


class SnapshotStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (Path(__file__).resolve().parents[2] / "outputs")

    def save(self, command: str, payload: Any) -> tuple[Path, Path]:
        now = datetime.now(settings.timezone)
        target_dir = self.base_dir / command / now.strftime("%Y-%m-%d")
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = now.strftime('%H%M%S-%f')

        json_path = target_dir / f"{stem}.json"
        data = to_dict(payload)
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        csv_path = target_dir / f"{stem}.csv"
        self._write_csv(csv_path, command, data)
        return json_path, csv_path

    def _write_csv(self, path: Path, command: str, data: dict[str, Any]) -> None:
        if command in {"discover", "scan"}:
            rows = data.get("tokens") or []
            if not rows:
                rows = [{k: v for k, v in data.items() if k != "tokens"}]
            self._write_rows(path, rows)
            return

        if command == "prelaunch":
            rows = data.get("projects") or []
            if not rows:
                rows = [{k: v for k, v in data.items() if k != "projects"}]
            self._write_rows(path, rows)
            return

        if command == "analyze":
            flat = self._flatten_dict(data)
            self._write_rows(path, [flat])
            return

        self._write_rows(path, [self._flatten_dict(data)])

    def _write_rows(self, path: Path, rows: list[dict[str, Any]]) -> None:
        normalized = [self._flatten_dict(row) for row in rows]
        fieldnames: list[str] = []
        for row in normalized:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in normalized:
                writer.writerow(row)

    def _flatten_dict(self, value: Any, prefix: str = "") -> dict[str, Any]:
        if isinstance(value, dict):
            flat: dict[str, Any] = {}
            for key, nested in value.items():
                nested_prefix = f"{prefix}.{key}" if prefix else str(key)
                flat.update(self._flatten_dict(nested, nested_prefix))
            return flat
        if isinstance(value, list):
            if all(not isinstance(item, (dict, list)) for item in value):
                return {prefix: " | ".join("" if item is None else str(item) for item in value)}
            return {prefix: json.dumps(value, ensure_ascii=False)}
        return {prefix: value}
