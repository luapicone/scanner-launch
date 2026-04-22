from __future__ import annotations

from datetime import datetime

from scanner_launch.config import settings
from scanner_launch.models import BatchScanResult, to_dict, now_art
from scanner_launch.services.discovery import DiscoveryService
from scanner_launch.services.risk import RiskAnalyzerService


class BatchScanService:
    def __init__(self, discovery_service: DiscoveryService | None = None, risk_service: RiskAnalyzerService | None = None) -> None:
        self.discovery_service = discovery_service or DiscoveryService()
        self.risk_service = risk_service or RiskAnalyzerService()

    def scan(self, limit: int = 20, max_age_hours: int = 24) -> BatchScanResult:
        discovery = self.discovery_service.discover(limit=limit, max_age_hours=max_age_hours)
        warnings = list(discovery.warnings)
        if discovery.error and not discovery.tokens:
            return BatchScanResult(
                tokens=[],
                source=discovery.source,
                fetchedAt=now_art(datetime.now(settings.timezone)),
                error=discovery.error,
                warnings=warnings,
            )

        evaluated: list[dict] = []
        for token in discovery.tokens:
            result = self.risk_service.analyze(token.symbol or token.name or token.id, chain=token.chain)
            item = to_dict(result)
            item.setdefault("name", token.name)
            item.setdefault("symbol", token.symbol)
            item.setdefault("chain", token.chain)
            item["launchTime"] = token.launchTime
            item["launchAgo"] = token.launchAgo
            item["buyPlatform"] = item.get("buyPlatform") or token.buyPlatform
            item["buyLink"] = item.get("buyLink") or token.buyLink
            item["buyWhere"] = item.get("buyWhere") or token.buyWhere
            item["buyLabel"] = item.get("buyLabel") or token.buyLabel
            item["buyNote"] = item.get("buyNote") or token.buyNote
            item["hasDirectBuy"] = bool(item.get("hasDirectBuy") or token.hasDirectBuy)
            evaluated.append(item)

        evaluated.sort(key=lambda item: item.get("overallScore", 0), reverse=True)
        return BatchScanResult(
            tokens=evaluated,
            source=discovery.source,
            fetchedAt=now_art(datetime.now(settings.timezone)),
            warnings=warnings,
        )
