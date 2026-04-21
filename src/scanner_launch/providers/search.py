from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from scanner_launch.config import settings
from scanner_launch.models import SearchHit


DEFAULT_DISCOVERY_QUERIES = [
    "site:dexscreener.com new tokens today 2026",
    "coingecko new cryptocurrencies listed today",
    "new token launch solana ethereum bsc today",
    "dexscreener latest token profiles",
]


@dataclass
class SearchProvider:
    name: str = "dexscreener"
    base_url: str = "https://api.dexscreener.com"

    def _get_json(self, path: str) -> Any:
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": settings.user_agent,
            },
        )
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def search(self, query: str, limit: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                title="Query search not wired yet",
                url="—",
                snippet=f"Hybrid web search not implemented yet for query: {query}",
                provider=self.name,
            )
        ][:limit]

    def latest_token_profiles(self, limit: int = 20) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        try:
            payload = self._get_json("/token-profiles/latest/v1")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"DexScreener token profiles unavailable: {exc}")
            return [], warnings

        if not isinstance(payload, list):
            warnings.append("DexScreener token profiles returned unexpected payload")
            return [], warnings

        return payload[:limit], warnings

    def token_pairs(self, chain_id: str, token_address: str) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        safe_chain = quote(chain_id, safe="")
        safe_token = quote(token_address, safe="")
        try:
            payload = self._get_json(f"/token-pairs/v1/{safe_chain}/{safe_token}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"DexScreener token pairs unavailable for {chain_id}:{token_address}: {exc}")
            return [], warnings

        if not isinstance(payload, list):
            warnings.append(f"DexScreener token pairs returned unexpected payload for {chain_id}:{token_address}")
            return [], warnings

        return payload, warnings

    def pair_detail(self, chain_id: str, pair_address: str) -> tuple[dict[str, Any] | None, list[str]]:
        warnings: list[str] = []
        safe_chain = quote(chain_id, safe="")
        safe_pair = quote(pair_address, safe="")
        try:
            payload = self._get_json(f"/latest/dex/pairs/{safe_chain}/{safe_pair}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"DexScreener pair detail unavailable for {chain_id}:{pair_address}: {exc}")
            return None, warnings

        if not isinstance(payload, dict):
            warnings.append(f"DexScreener pair detail returned unexpected payload for {chain_id}:{pair_address}")
            return None, warnings

        pair = payload.get("pair")
        if not isinstance(pair, dict):
            warnings.append(f"DexScreener pair detail missing pair object for {chain_id}:{pair_address}")
            return None, warnings

        return pair, warnings

    def search_pairs(self, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        safe_query = quote(query, safe="")
        try:
            payload = self._get_json(f"/latest/dex/search?q={safe_query}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"DexScreener search unavailable for {query}: {exc}")
            return [], warnings

        if not isinstance(payload, dict):
            warnings.append(f"DexScreener search returned unexpected payload for {query}")
            return [], warnings

        pairs = payload.get("pairs") or []
        if not isinstance(pairs, list):
            warnings.append(f"DexScreener search missing pairs for {query}")
            return [], warnings

        return pairs, warnings
