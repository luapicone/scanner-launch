from __future__ import annotations

from datetime import datetime

from scanner_launch.config import settings
from scanner_launch.models import SearchHit, TokenRecord, now_art


class TokenExtractor:
    def extract_token_candidates(self, hits: list[SearchHit], max_age_hours: int = 6) -> tuple[list[TokenRecord], list[str]]:
        warnings: list[str] = []
        tokens: list[TokenRecord] = []
        seen_ids: set[str] = set()

        for hit in hits:
            payload = hit.payload or {}
            profile = payload.get("profile") or {}
            pair = payload.get("pair") or {}
            pair_created_at = pair.get("pairCreatedAt")

            if not pair_created_at:
                warnings.append(f"Missing pairCreatedAt for {profile.get('tokenAddress', hit.url)}")
                continue

            launch_dt = datetime.fromtimestamp(pair_created_at / 1000, tz=settings.timezone)
            age_hours = (datetime.now(settings.timezone) - launch_dt).total_seconds() / 3600
            if age_hours > max_age_hours:
                continue

            base_token = pair.get("baseToken") or {}
            info = pair.get("info") or {}
            socials = {str(item.get('type', '')).lower() for item in info.get("socials", [])}
            websites = info.get("websites", [])
            dex_id = str(pair.get("dexId", "—"))
            chain = str(profile.get("chainId") or pair.get("chainId") or "—")
            name = str(base_token.get("name") or "—")
            symbol = str(base_token.get("symbol") or "—")
            token_id = self._build_token_id(name, symbol, chain)
            if token_id in seen_ids:
                continue
            seen_ids.add(token_id)

            tokens.append(
                TokenRecord(
                    id=token_id,
                    name=name,
                    symbol=symbol,
                    chain=chain,
                    price=self._format_price(pair.get("priceUsd")),
                    marketCap=self._format_money(pair.get("marketCap") or pair.get("fdv")),
                    liquidity=self._format_money((pair.get("liquidity") or {}).get("usd")),
                    volume24h=self._format_money((pair.get("volume") or {}).get("h24")),
                    launchTime=now_art(launch_dt),
                    launchAgo=self._format_ago(age_hours),
                    buyPlatform=[dex_id] if dex_id != "—" else [],
                    buyLink=str(pair.get("url") or profile.get("url") or "—"),
                    website="sí" if websites else "no",
                    twitter="sí" if "twitter" in socials else "no",
                    telegram="sí" if "telegram" in socials else "no",
                    extra=str(profile.get("description") or "—"),
                    description=str(profile.get("description") or "—"),
                    sourceUrl=str(profile.get("url") or pair.get("url") or "—"),
                )
            )

        return tokens, warnings

    def _build_token_id(self, name: str, symbol: str, chain: str) -> str:
        raw = f"{name}-{symbol}-{chain}".strip().lower()
        return "-".join(raw.replace("$", "").split())

    def _format_price(self, value) -> str:
        number = self._to_float(value)
        if number is None:
            return "—"
        if number >= 1:
            return f"${number:,.4f}"
        return f"${number:.10f}".rstrip("0").rstrip(".")

    def _format_money(self, value) -> str:
        number = self._to_float(value)
        if number is None:
            return "—"
        abs_number = abs(number)
        if abs_number >= 1_000_000_000:
            return f"${number / 1_000_000_000:.2f}B"
        if abs_number >= 1_000_000:
            return f"${number / 1_000_000:.2f}M"
        if abs_number >= 1_000:
            return f"${number / 1_000:.2f}K"
        return f"${number:.2f}"

    def _format_ago(self, age_hours: float) -> str:
        if age_hours < 1:
            minutes = max(1, int(round(age_hours * 60)))
            return f"hace {minutes} minutos"
        hours = int(age_hours)
        minutes = int(round((age_hours - hours) * 60))
        if minutes <= 0:
            return f"hace {hours} horas"
        return f"hace {hours}h {minutes}m"

    def _to_float(self, value):
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
