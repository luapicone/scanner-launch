from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any


@dataclass
class TokenRecord:
    id: str
    name: str
    symbol: str
    chain: str
    price: str = "—"
    marketCap: str = "—"
    liquidity: str = "—"
    volume24h: str = "—"
    launchTime: str = "—"
    launchAgo: str = "—"
    buyPlatform: list[str] = field(default_factory=list)
    buyLink: str = "—"
    buyWhere: str = "—"
    buyLabel: str = "Abrir mercado"
    buyNote: str = "—"
    hasDirectBuy: bool = False
    website: str = "no"
    twitter: str = "no"
    telegram: str = "no"
    extra: str = "—"
    description: str = "—"
    sourceUrl: str = "—"


@dataclass
class DiscoveryResult:
    tokens: list[TokenRecord] = field(default_factory=list)
    source: str = "—"
    fetchedAt: str = "—"
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class RiskScores:
    liquidez: int
    volumen: int
    comunidad: int
    transparencia: int
    onchain: int


@dataclass
class RiskAnalysisResult:
    riskLevel: str
    overallScore: int
    scores: RiskScores
    redFlags: list[str] = field(default_factory=list)
    greenFlags: list[str] = field(default_factory=list)
    verdict: str = ""
    analysis: str = ""
    tokenId: str | None = None
    fetchedAt: str | None = None
    name: str | None = None
    symbol: str | None = None
    chain: str | None = None
    launchTime: str | None = None
    launchAgo: str | None = None
    buyPlatform: list[str] = field(default_factory=list)
    buyLink: str | None = None
    buyWhere: str | None = None
    buyLabel: str | None = None
    buyNote: str | None = None
    hasDirectBuy: bool = False
    projection: str | None = None


@dataclass
class BatchScanResult:
    tokens: list[dict[str, Any]] = field(default_factory=list)
    source: str = "—"
    fetchedAt: str = "—"
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class PrelaunchProject:
    id: str
    name: str
    symbol: str
    source: str
    sourceUrl: str
    projectUrl: str
    chain: str
    stage: str
    launchTime: str
    launchAgo: str
    websiteUrl: str
    twitterUrl: str
    telegramUrl: str
    docsUrl: str
    buyPlatform: list[str] = field(default_factory=list)
    buyLink: str = "—"
    buyWhere: str = "—"
    buyLabel: str = "Ver proyecto"
    buyNote: str = "—"
    hasDirectBuy: bool = False
    categories: list[str] = field(default_factory=list)
    investorsCount: int | None = None
    fundingUsd: str = "—"
    scores: dict[str, int] = field(default_factory=dict)
    overallScore: int = 0
    riskLevel: str = "—"
    redFlags: list[str] = field(default_factory=list)
    greenFlags: list[str] = field(default_factory=list)
    projection: str = "—"
    buyVerdict: str = "—"
    analysis: str = "—"
    fetchedAt: str | None = None


@dataclass
class PrelaunchResult:
    projects: list[PrelaunchProject] = field(default_factory=list)
    source: str = "—"
    fetchedAt: str = "—"
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    provider: str = "manual"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanRequest:
    limit: int = 12
    max_age_hours: int = 6
    query_set: list[str] = field(default_factory=list)


@dataclass
class AnalyzeRequest:
    token: str
    chain: str | None = None


def now_art(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def to_dict(value):
    if is_dataclass(value):
        return asdict(value)
    return value
