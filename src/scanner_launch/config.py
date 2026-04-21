from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    timezone_name: str = os.getenv("SCANNER_TIMEZONE", "America/Argentina/Buenos_Aires")
    default_limit: int = int(os.getenv("SCANNER_DEFAULT_LIMIT", "12"))
    user_agent: str = os.getenv("SCANNER_USER_AGENT", "scanner-launch/0.1")

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


settings = Settings()
