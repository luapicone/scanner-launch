from __future__ import annotations

from datetime import datetime

from scanner_launch.config import settings
from scanner_launch.models import DiscoveryResult, ScanRequest, SearchHit, now_art
from scanner_launch.providers.extractors import TokenExtractor
from scanner_launch.providers.search import DEFAULT_DISCOVERY_QUERIES, SearchProvider


class DiscoveryService:
    def __init__(self, search_provider: SearchProvider | None = None, extractor: TokenExtractor | None = None) -> None:
        self.search_provider = search_provider or SearchProvider()
        self.extractor = extractor or TokenExtractor()

    def discover(self, limit: int | None = None, max_age_hours: int = 6) -> DiscoveryResult:
        query_limit = limit or settings.default_limit
        request = ScanRequest(limit=query_limit, max_age_hours=max_age_hours, query_set=DEFAULT_DISCOVERY_QUERIES)

        warnings: list[str] = []
        profiles, profile_warnings = self.search_provider.latest_token_profiles(limit=max(query_limit * 3, 24))
        warnings.extend(profile_warnings)

        enriched_hits: list[SearchHit] = []
        for profile in profiles:
            chain_id = str(profile.get("chainId") or "")
            token_address = str(profile.get("tokenAddress") or "")
            if not chain_id or not token_address:
                warnings.append(f"DexScreener profile incompleto: {profile}")
                continue

            pairs, pair_warnings = self.search_provider.token_pairs(chain_id=chain_id, token_address=token_address)
            warnings.extend(pair_warnings)
            if not pairs:
                continue

            best_pair = sorted(
                pairs,
                key=lambda pair: float((pair.get("volume") or {}).get("h24") or 0),
                reverse=True,
            )[0]
            pair_address = str(best_pair.get("pairAddress") or "")
            if pair_address:
                pair_detail, detail_warnings = self.search_provider.pair_detail(chain_id=chain_id, pair_address=pair_address)
                warnings.extend(detail_warnings)
                if pair_detail:
                    best_pair = pair_detail

            enriched_hits.append(
                SearchHit(
                    title=str((best_pair.get("baseToken") or {}).get("name") or token_address),
                    url=str(best_pair.get("url") or profile.get("url") or "—"),
                    provider=self.search_provider.name,
                    payload={"profile": profile, "pair": best_pair},
                )
            )

        tokens, extract_warnings = self.extractor.extract_token_candidates(enriched_hits, max_age_hours=request.max_age_hours)
        warnings.extend(extract_warnings)
        tokens = sorted(tokens, key=lambda token: self._sort_minutes(token.launchAgo))[: request.limit]

        if not tokens:
            return DiscoveryResult(
                tokens=[],
                source="DexScreener",
                fetchedAt=now_art(datetime.now(settings.timezone)),
                error="No se encontraron tokens nuevos en este momento. Reintentá en 60 segundos.",
                warnings=warnings or ["DexScreener no devolvió pares recientes utilizables en esta corrida."],
            )

        return DiscoveryResult(
            tokens=tokens,
            source="DexScreener",
            fetchedAt=now_art(datetime.now(settings.timezone)),
            warnings=warnings,
        )

    def _sort_minutes(self, launch_ago: str) -> int:
        if "minutos" in launch_ago:
            return int("".join(ch for ch in launch_ago if ch.isdigit()) or 999999)
        if "hace" in launch_ago and "h" in launch_ago:
            digits = [int(part[:-1]) for part in launch_ago.split() if part.endswith("h") and part[:-1].isdigit()]
            mins = [int(part[:-1]) for part in launch_ago.split() if part.endswith("m") and part[:-1].isdigit()]
            return (digits[0] if digits else 999) * 60 + (mins[0] if mins else 0)
        if "horas" in launch_ago:
            digits = int("".join(ch for ch in launch_ago if ch.isdigit()) or 999)
            return digits * 60
        return 999999
