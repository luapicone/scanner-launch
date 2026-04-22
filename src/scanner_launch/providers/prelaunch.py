from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from scanner_launch.config import settings


@dataclass
class PrelaunchProvider:
    user_agent: str = settings.user_agent

    def fetch_projects(self, limit: int = 20) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        projects: list[dict[str, Any]] = []

        ico_projects, ico_warnings = self._fetch_icoanalytics(limit=limit)
        warnings.extend(ico_warnings)
        projects.extend(ico_projects)

        cmc_projects, cmc_warnings = self._fetch_cmc_upcoming(limit=limit)
        warnings.extend(cmc_warnings)
        projects.extend(cmc_projects)

        deduped: dict[str, dict[str, Any]] = {}
        now_ms = int(datetime.now(settings.timezone).timestamp() * 1000)
        for project in projects:
            launch_ts = project.get("launch_ts")
            if launch_ts and launch_ts < now_ms:
                continue
            key = self._normalize_id(project.get("name"), project.get("symbol"), None)
            existing = deduped.get(key)
            if existing is None or self._project_quality(project) > self._project_quality(existing):
                deduped[key] = project

        ordered = sorted(deduped.values(), key=lambda item: item.get("launch_ts") or 10**18)
        return ordered[:limit], warnings

    def _fetch_icoanalytics(self, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        url = "https://icoanalytics.org/token-generation-events/"
        html_text = self._fetch_html(url, warnings, label="ICO Analytics calendar")
        if not html_text:
            return [], warnings

        pattern = re.compile(
            r'<div class="hp-table-row hpt-data"[^>]*data-logicstart="(?P<logicstart>[^"]*)"[^>]*>.*?'
            r'<a class="t-project-link" href="(?P<project_url>[^"]+)">.*?'
            r'<h5 class="cointitle">(?P<name>[^<]+)</h5>\s*<span class="cointag">(?P<symbol>[^<]*)</span>.*?'
            r'<div class="hpt-col3">(?P<launch_text>[^<]+)</div>.*?'
            r'<div class="hpt-col4">\s*(?P<stage>[^<]+?)\s*</div>.*?'
            r'<div class="hpt-col4 pluscentresm">\s*(?P<investors>[^<]+?)\s*</div>.*?'
            r'<div class="hpt-col5 numeric abbrusd">(?P<funding>[^<]+)</div>.*?'
            r'<div class="hpt-col6">(?P<categories>.*?)</div></div>',
            re.S,
        )

        rows = []
        for match in pattern.finditer(html_text):
            categories = re.findall(r'<span[^>]*>([^<]+)</span>', match.group("categories"))
            project_url = html.unescape(match.group("project_url").strip())
            detail = self._fetch_icoanalytics_project(project_url, warnings)
            rows.append(
                {
                    "id": self._normalize_id(match.group("name"), match.group("symbol"), "icoanalytics"),
                    "name": html.unescape(match.group("name").strip()),
                    "symbol": html.unescape(match.group("symbol").strip() or "—"),
                    "source": "ICO Analytics",
                    "sourceUrl": url,
                    "projectUrl": project_url,
                    "launchText": html.unescape(match.group("launch_text").strip()),
                    "launch_ts": self._parse_logicstart(match.group("logicstart")),
                    "stage": html.unescape(match.group("stage").strip()),
                    "investorsCount": self._to_int(match.group("investors")),
                    "fundingUsd": self._format_money(self._to_float(match.group("funding"))),
                    "fundingValue": self._to_float(match.group("funding")),
                    "categories": [html.unescape(cat.strip()) for cat in categories if cat.strip()],
                    **detail,
                }
            )
            if len(rows) >= limit:
                break

        if not rows:
            warnings.append("ICO Analytics returned no parseable rows")
        return rows, warnings

    def _fetch_icoanalytics_project(self, url: str, warnings: list[str]) -> dict[str, Any]:
        html_text = self._fetch_html(url, warnings, label=f"ICO Analytics project {url}")
        if not html_text:
            return {}

        description = self._extract_meta_description(html_text)
        links_block = self._extract_icoanalytics_links_block(html_text)
        named_links = self._extract_icoanalytics_named_links(links_block or html_text)
        links = self._extract_links(links_block or html_text)
        website_url = self._pick_named_link(named_links, ["website"]) or self._pick_website(links)
        docs_url = self._pick_named_link(named_links, ["docs", "litepaper", "whitepaper"]) or self._pick_docs(links)
        twitter_url = self._pick_named_link(named_links, ["twitter", "x ("]) or self._pick_social(links, ["twitter.com", "x.com"])
        telegram_url = self._pick_named_link(named_links, ["telegram", "tg"]) or self._pick_social(links, ["t.me/", "telegram.me"])
        if telegram_url and "ico_analytic" in telegram_url:
            telegram_url = None
        chain = self._infer_chain(description, [], html_text)

        return {
            "description": description,
            "websiteUrl": website_url,
            "docsUrl": docs_url,
            "twitterUrl": twitter_url,
            "telegramUrl": telegram_url,
            "chain": chain,
        }

    def _fetch_cmc_upcoming(self, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        url = "https://coinmarketcap.com/upcoming/"
        html_text = self._fetch_html(url, warnings, label="CoinMarketCap upcoming")
        if not html_text:
            return [], warnings

        rows: list[dict[str, Any]] = []
        segments = html_text.split('<tr style="cursor:pointer">')
        for segment in segments[1:]:
            href_match = re.search(r'<a href="(?P<href>/currencies/[^"]+/)" class="cmc-link">', segment)
            name_match = re.search(r'alt="[^"]+ logo".*?<p[^>]*font-weight="semibold"[^>]*>(?P<name>[^<]+)</p>.*?coin-item-symbol[^>]*>(?P<symbol>[^<]+)</p>', segment, re.S)
            date_match = re.search(r'</a></td><td style="text-align:end"><div[^>]*>.*?(?P<date>(?:[A-Za-z]+\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4},\s+\d{2}:\d{2}(?::\d{2})?))</div>', segment, re.S)
            if not href_match or not name_match or not date_match:
                continue

            project_url = urljoin(url, html.unescape(href_match.group("href")))
            detail = self._fetch_cmc_project(project_url, warnings)
            launch_text = html.unescape(date_match.group("date").strip())
            rows.append(
                {
                    "id": self._normalize_id(name_match.group("name"), name_match.group("symbol"), "cmc"),
                    "name": html.unescape(name_match.group("name").strip()),
                    "symbol": html.unescape(name_match.group("symbol").strip()),
                    "source": "CoinMarketCap Upcoming",
                    "sourceUrl": url,
                    "projectUrl": project_url,
                    "launchText": launch_text,
                    "launch_ts": self._parse_cmc_datetime(launch_text),
                    "stage": "Upcoming listing",
                    "investorsCount": None,
                    "fundingUsd": "—",
                    "fundingValue": None,
                    "categories": detail.get("categories", []),
                    **detail,
                }
            )
            if len(rows) >= limit:
                break

        if not rows:
            warnings.append("CoinMarketCap Upcoming returned no parseable rows")
        return rows, warnings

    def _fetch_cmc_project(self, url: str, warnings: list[str]) -> dict[str, Any]:
        html_text = self._fetch_html(url, warnings, label=f"CoinMarketCap project {url}")
        if not html_text:
            return {}

        description = self._extract_meta_description(html_text)
        website_links = re.findall(r'href="([^"]+)"[^>]*data-test="chip-website-link"', html_text)
        social_links = re.findall(r'href="([^"]+)"[^>]*data-test="chip-social-link"', html_text)
        all_links = [self._normalize_protocol(link) for link in website_links + social_links]
        categories = re.findall(r'"category":"([^"]+)"', html_text)
        chain = self._extract_contract_platform(html_text)
        return {
            "description": description,
            "websiteUrl": self._pick_website(all_links),
            "docsUrl": self._pick_docs(all_links),
            "twitterUrl": self._pick_social(all_links, ["twitter.com", "x.com"]),
            "telegramUrl": self._pick_social(all_links, ["t.me", "telegram.me"]),
            "chain": chain,
            "categories": [html.unescape(cat) for cat in categories[:3]],
        }

    def _fetch_html(self, url: str, warnings: list[str], label: str) -> str | None:
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"})
        try:
            with urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8", "ignore")
        except (HTTPError, URLError, TimeoutError) as exc:
            warnings.append(f"{label} unavailable: {exc}")
            return None

    def _extract_meta_description(self, html_text: str) -> str:
        for pattern in [r'<meta name="description" content="([^"]+)"', r'<meta property="og:description" content="([^"]+)"']:
            match = re.search(pattern, html_text)
            if match:
                return html.unescape(match.group(1).strip())
        return "—"

    def _extract_links(self, html_text: str) -> list[str]:
        raw = re.findall(r'href="(https?://[^"]+)"', html_text)
        links = []
        for link in raw:
            norm = self._normalize_protocol(html.unescape(link))
            if norm not in links:
                links.append(norm)
        return links

    def _extract_icoanalytics_named_links(self, html_text: str) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for href, inner in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*class="linkwithicon"[^>]*>(.*?)</a>', html_text, re.S):
            label = re.sub(r'<[^>]+>', ' ', inner)
            label = " ".join(html.unescape(label).split()).strip().lower()
            items.append((self._normalize_protocol(html.unescape(href)), label))
        return items

    def _extract_icoanalytics_links_block(self, html_text: str) -> str | None:
        match = re.search(r'Project links and categories</div><div class="spoiler-content">(?P<block>.*?)<div class="spoiler-close">', html_text, re.S)
        if match:
            return match.group("block")
        return None

    def _pick_named_link(self, items: list[tuple[str, str]], labels: list[str]) -> str | None:
        for href, label in items:
            if any(key in label for key in labels):
                return href
        return None

    def _pick_website(self, links: list[str]) -> str | None:
        blocked = [
            "icoanalytics.org",
            "coinmarketcap.com",
            "twitter.com",
            "x.com",
            "t.me",
            "telegram.me",
            "medium.com",
            "discord.com",
            "github.com",
            "docs.",
            "whitepaper",
            "gmpg.org",
            "wp-content",
        ]
        for link in links:
            if not any(block in link for block in blocked):
                return link
        return None

    def _pick_docs(self, links: list[str]) -> str | None:
        for link in links:
            if any(key in link.lower() for key in ["docs", "whitepaper", "litepaper", "gitbook"]):
                return link
        return None

    def _pick_social(self, links: list[str], domains: list[str]) -> str | None:
        for link in links:
            if any(domain in link for domain in domains):
                return link
        return None

    def _extract_contract_platform(self, html_text: str) -> str | None:
        match = re.search(r'"contractPlatform":"([^"]+)"', html_text)
        if match:
            return html.unescape(match.group(1))
        return None

    def _infer_chain(self, description: str, categories: list[str], html_text: str) -> str | None:
        haystack = " ".join([description, " ".join(categories), html_text[:5000]]).lower()
        mapping = [
            ("solana", "solana"),
            ("ethereum", "ethereum"),
            ("base", "base"),
            ("polygon", "polygon"),
            ("bnb", "bsc"),
            ("zksync", "zksync"),
            ("hyperliquid", "hyperliquid"),
            ("polkadot", "polkadot"),
        ]
        for needle, label in mapping:
            if needle in haystack:
                return label
        return None

    def _parse_logicstart(self, value: str) -> int | None:
        try:
            dt = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
            return int(dt.replace(tzinfo=settings.timezone).timestamp() * 1000)
        except Exception:
            return None

    def _parse_cmc_datetime(self, value: str) -> int | None:
        for fmt in ["%b %d, %Y, %H:%M:%S", "%b %d, %Y, %H:%M", "%B %Y", "%b %Y"]:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return int(dt.replace(tzinfo=settings.timezone).timestamp() * 1000)
            except Exception:
                continue
        return None

    def _format_money(self, value: float | None) -> str:
        if value is None:
            return "—"
        abs_value = abs(value)
        if abs_value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if abs_value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if abs_value >= 1_000:
            return f"${value / 1_000:.2f}K"
        return f"${value:.2f}"

    def _to_float(self, value: str | None) -> float | None:
        try:
            if value in (None, "", "-"):
                return None
            cleaned = re.sub(r"[^0-9.]", "", value)
            return float(cleaned) if cleaned else None
        except Exception:
            return None

    def _to_int(self, value: str | None) -> int | None:
        try:
            if value in (None, "", "-"):
                return None
            cleaned = re.sub(r"[^0-9]", "", value)
            return int(cleaned) if cleaned else None
        except Exception:
            return None

    def _normalize_protocol(self, link: str) -> str:
        if link.startswith("//"):
            return f"https:{link}"
        return link

    def _normalize_id(self, name: str | None, symbol: str | None, source: str | None) -> str:
        raw = f"{name or 'unknown'}-{symbol or 'unknown'}-{source or 'source'}".lower()
        return "-".join(raw.replace("$", "").split())

    def _project_quality(self, project: dict[str, Any]) -> int:
        score = 0
        for key in ["websiteUrl", "twitterUrl", "telegramUrl", "docsUrl"]:
            if project.get(key):
                score += 1
        if project.get("investorsCount"):
            score += 2
        if project.get("fundingValue"):
            score += 2
        if project.get("launch_ts"):
            score += 1
        if project.get("chain"):
            score += 1
        return score
