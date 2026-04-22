from __future__ import annotations

from datetime import datetime

from scanner_launch.buy_links import build_live_buy_target, prettify_dex
from scanner_launch.config import settings
from scanner_launch.models import AnalyzeRequest, RiskAnalysisResult, RiskScores, now_art
from scanner_launch.providers.search import SearchProvider


class RiskAnalyzerService:
    def __init__(self, search_provider: SearchProvider | None = None) -> None:
        self.search_provider = search_provider or SearchProvider()

    def analyze(self, token: str, chain: str | None = None) -> RiskAnalysisResult:
        request = AnalyzeRequest(token=token, chain=chain)
        warnings: list[str] = []
        pairs, search_warnings = self.search_provider.search_pairs(request.token)
        warnings.extend(search_warnings)

        pair = self._select_pair(pairs, request.token, request.chain)
        if not pair:
            return RiskAnalysisResult(
                tokenId=f"{request.token.lower()}-{(request.chain or 'unknown').lower()}",
                fetchedAt=now_art(datetime.now(settings.timezone)),
                riskLevel="ALTO RIESGO",
                overallScore=15,
                scores=RiskScores(liquidez=0, volumen=0, comunidad=0, transparencia=0, onchain=0),
                redFlags=[f"No se encontró un par verificable en DexScreener para {request.token}"],
                greenFlags=[],
                verdict="Sin par verificable en una DEX reconocida dentro de esta integración. Riesgo extremadamente alto.",
                analysis="El analizador no encontró un par usable para este token en DexScreener con los datos disponibles en esta corrida. Sin mercado verificable, no conviene tratarlo como oportunidad operable.",
                name=request.token,
                symbol=request.token,
                chain=request.chain,
                projection="Sin proyección confiable por falta de mercado verificable.",
            )

        pair_address = str(pair.get("pairAddress") or "")
        chain_id = str(pair.get("chainId") or request.chain or "unknown")
        if pair_address:
            pair_detail, detail_warnings = self.search_provider.pair_detail(chain_id=chain_id, pair_address=pair_address)
            warnings.extend(detail_warnings)
            if pair_detail:
                merged_info = {**(pair.get("info") or {}), **(pair_detail.get("info") or {})}
                pair = {**pair, **pair_detail, "info": merged_info}

        liquidity_usd = self._to_float((pair.get("liquidity") or {}).get("usd"))
        volume_usd = self._to_float((pair.get("volume") or {}).get("h24"))
        market_cap = self._to_float(pair.get("marketCap") or pair.get("fdv"))
        pair_created_at = self._to_float(pair.get("pairCreatedAt"))
        info = pair.get("info") or {}
        description = str(info.get("description") or "")
        socials = {str(item.get("type") or "").lower() for item in info.get("socials", [])}
        websites = info.get("websites") or []

        liquidity_score = self._score_liquidity(liquidity_usd)
        volume_score = self._score_volume(liquidity_usd, volume_usd)
        community_score = self._score_community(websites=websites, socials=socials)
        transparency_score = self._score_transparency(info=info)
        onchain_score = self._score_onchain(liquidity_usd=liquidity_usd, market_cap=market_cap, pair_created_at=pair_created_at)

        scores = RiskScores(
            liquidez=liquidity_score,
            volumen=volume_score,
            comunidad=community_score,
            transparencia=transparency_score,
            onchain=onchain_score,
        )
        overall_score = round(
            (liquidity_score * 0.30)
            + (volume_score * 0.20)
            + (community_score * 0.20)
            + (transparency_score * 0.10)
            + (onchain_score * 0.20)
        )

        red_flags, green_flags = self._build_flags(
            pair=pair,
            liquidity_usd=liquidity_usd,
            volume_usd=volume_usd,
            market_cap=market_cap,
            pair_created_at=pair_created_at,
            websites=websites,
            socials=socials,
        )
        red_flags.extend(warnings)
        risk_level = self._risk_level(overall_score)
        verdict = self._build_verdict(risk_level, overall_score, liquidity_usd, volume_usd)
        analysis = self._build_analysis(
            risk_level=risk_level,
            overall_score=overall_score,
            liquidity_usd=liquidity_usd,
            volume_usd=volume_usd,
            market_cap=market_cap,
            community_score=community_score,
            transparency_score=transparency_score,
            onchain_score=onchain_score,
            red_flags=red_flags,
        )

        base_token = pair.get("baseToken") or {}
        launch_time = self._format_launch_time(pair_created_at)
        launch_ago = self._format_launch_ago(pair_created_at)
        buy_target = build_live_buy_target(
            chain_id,
            str(base_token.get('address') or ''),
            str(pair.get('dexId') or ''),
            str(pair.get('url') or '—'),
        )
        return RiskAnalysisResult(
            tokenId=f"{str(base_token.get('symbol') or request.token).lower()}-{chain_id.lower()}",
            fetchedAt=now_art(datetime.now(settings.timezone)),
            riskLevel=risk_level,
            overallScore=overall_score,
            scores=scores,
            redFlags=red_flags,
            greenFlags=green_flags,
            verdict=verdict,
            analysis=analysis,
            name=str(base_token.get('name') or request.token),
            symbol=str(base_token.get('symbol') or request.token),
            chain=chain_id,
            launchTime=launch_time,
            launchAgo=launch_ago,
            buyPlatform=[prettify_dex(str(pair.get('dexId') or '—'))],
            buyLink=str(buy_target.get('buyLink') or '—'),
            buyWhere=str(buy_target.get('buyWhere') or '—'),
            buyLabel=str(buy_target.get('buyLabel') or 'Abrir mercado'),
            buyNote=str(buy_target.get('buyNote') or '—'),
            hasDirectBuy=bool(buy_target.get('hasDirectBuy')),
            projection=self._build_projection(risk_level, overall_score, liquidity_usd, volume_usd),
        )

    def _select_pair(self, pairs: list[dict], token: str, chain: str | None) -> dict | None:
        token_l = token.strip().lower()
        chain_l = chain.lower() if chain else None
        ranked: list[tuple[tuple[float, ...], dict]] = []

        for pair in pairs:
            base = pair.get("baseToken") or {}
            quote = pair.get("quoteToken") or {}
            labels = {str(label).lower() for label in (pair.get("labels") or [])}
            name = str(base.get("name") or "").strip().lower()
            symbol = str(base.get("symbol") or "").strip().lower()
            pair_chain = str(pair.get("chainId") or "").strip().lower()
            quote_symbol = str(quote.get("symbol") or "").strip().lower()
            dex_id = str(pair.get("dexId") or "").strip().lower()
            if chain_l and pair_chain != chain_l:
                continue

            exact_symbol = 1 if token_l == symbol else 0
            exact_name = 1 if token_l == name else 0
            word_name = 1 if token_l and token_l in {part for part in name.replace("-", " ").split()} else 0
            word_symbol = 1 if token_l and token_l in {part for part in symbol.replace("-", " ").split()} else 0
            partial = 1 if token_l and (token_l in name or token_l in symbol) else 0
            verified_boost = 1 if dex_id not in {"pumpfun"} else 0
            quote_boost = 2 if quote_symbol in {"usdc", "usdt", "sol", "wsol", "eth", "weth"} else 0
            label_boost = 1 if labels & {"dlmm", "v3", "clmm"} else 0
            liquidity = self._to_float((pair.get("liquidity") or {}).get("usd")) or 0
            volume = self._to_float((pair.get("volume") or {}).get("h24")) or 0
            market_cap = self._to_float(pair.get("marketCap") or pair.get("fdv")) or 0
            txns_h24 = pair.get("txns") or {}
            activity = ((txns_h24.get("h24") or {}).get("buys") or 0) + ((txns_h24.get("h24") or {}).get("sells") or 0)
            age = self._pair_age_hours(pair)
            age_boost = 1 if age is not None and age >= 24 else 0
            liq_to_mc = (liquidity / market_cap) if market_cap > 0 else 0

            match_score = exact_symbol * 100 + exact_name * 90 + word_symbol * 50 + word_name * 40 + partial * 10
            if match_score <= 0:
                continue

            ranked.append(((match_score, verified_boost, quote_boost, label_boost, age_boost, liq_to_mc, liquidity, volume, activity), pair))

        if not ranked and chain_l:
            for pair in pairs:
                pair_chain = str(pair.get("chainId") or "").strip().lower()
                if pair_chain != chain_l:
                    continue
                liquidity = self._to_float((pair.get("liquidity") or {}).get("usd")) or 0
                volume = self._to_float((pair.get("volume") or {}).get("h24")) or 0
                ranked.append(((0, 0, 0, 0, 0, 0, liquidity, volume, 0), pair))

        if not ranked:
            return None

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1]

    def _score_liquidity(self, liquidity_usd: float | None) -> int:
        if liquidity_usd is None:
            return 15
        if liquidity_usd < 10_000:
            return 5
        if liquidity_usd < 50_000:
            return 20
        if liquidity_usd < 500_000:
            return 45
        if liquidity_usd < 2_000_000:
            return 70
        return 90

    def _score_volume(self, liquidity_usd: float | None, volume_usd: float | None) -> int:
        if liquidity_usd is None or liquidity_usd <= 0 or volume_usd is None:
            return 25
        ratio = (volume_usd / liquidity_usd) * 100
        if ratio > 1000:
            return 10
        if ratio > 200:
            return 35
        if ratio >= 50:
            return 65
        return 90

    def _score_community(self, websites: list[dict], socials: set[str]) -> int:
        count = (1 if websites else 0) + sum(1 for key in {"twitter", "telegram"} if key in socials)
        if count == 0:
            return 10
        if count == 1:
            return 30
        if count == 2:
            return 55
        return 75

    def _score_transparency(self, info: dict) -> int:
        # DexScreener no entrega auditorías. Puntaje conservador si solo hay metadata básica.
        websites = info.get("websites") or []
        socials = info.get("socials") or []
        if websites or socials:
            return 20
        return 5

    def _score_onchain(self, liquidity_usd: float | None, market_cap: float | None, pair_created_at: float | None) -> int:
        score = 50
        age_hours = self._pair_age_hours({"pairCreatedAt": pair_created_at})
        if age_hours is not None:
            if age_hours < 1:
                score -= 20
            elif age_hours < 6:
                score -= 10
            else:
                score += 5
        if liquidity_usd is not None and market_cap is not None and liquidity_usd > 0:
            liq_to_mc = liquidity_usd / market_cap if market_cap > 0 else 0
            if liq_to_mc < 0.02:
                score -= 20
            elif liq_to_mc < 0.08:
                score -= 10
            else:
                score += 10
        return max(0, min(100, score))

    def _build_flags(self, pair: dict, liquidity_usd: float | None, volume_usd: float | None, market_cap: float | None, pair_created_at: float | None, websites: list[dict], socials: set[str]) -> tuple[list[str], list[str]]:
        red_flags: list[str] = []
        green_flags: list[str] = []
        desc = str((pair.get("info") or {}).get("description") or "")
        desc_lower = desc.lower()

        if liquidity_usd is not None and liquidity_usd < 10_000:
            red_flags.append("Liquidez menor a $10K")
        elif liquidity_usd is not None and liquidity_usd < 50_000:
            red_flags.append("Liquidez menor a $50K")
        if liquidity_usd is not None and liquidity_usd > 500_000:
            green_flags.append("Liquidez superior a $500K")
        if volume_usd is not None and liquidity_usd:
            ratio = (volume_usd / liquidity_usd) * 100 if liquidity_usd > 0 else 0
            if ratio > 1000:
                red_flags.append("Volumen/Liquidez > 1000%, posible wash trading")
            elif ratio > 200:
                red_flags.append("Volumen/Liquidez elevado, comportamiento sospechoso")
            elif ratio < 50:
                green_flags.append("Volumen/Liquidez relativamente orgánico")
        elif volume_usd is None:
            red_flags.append("Volumen 24h no disponible en la API para este par")
        if not websites and not ({"twitter", "telegram"} & socials):
            red_flags.append("Sin website, Twitter ni Telegram")
        elif websites:
            green_flags.append("Tiene website visible")
        if "twitter" in socials:
            green_flags.append("Tiene Twitter/X activo")
        if "telegram" in socials:
            green_flags.append("Tiene Telegram activo")
        if any(term in desc_lower for term in ["garantizado", "1000x seguro", "sin riesgo"]):
            red_flags.append("Lenguaje promocional extremo en la descripción")
        if pair_created_at is not None and market_cap is not None and liquidity_usd is not None:
            age_hours = self._pair_age_hours({"pairCreatedAt": pair_created_at})
            if age_hours is not None and age_hours < 1 and market_cap > 10_000_000 and liquidity_usd < 50_000:
                red_flags.append("Lanzado hace menos de 1 hora con market cap alto y poca liquidez")
        if liquidity_usd is None:
            red_flags.append("Liquidez no disponible en la API para este par")
        green_flags = list(dict.fromkeys(green_flags))
        red_flags = list(dict.fromkeys(red_flags))
        return red_flags, green_flags

    def _risk_level(self, overall_score: int) -> str:
        if overall_score <= 25:
            return "SCAM"
        if overall_score <= 45:
            return "ALTO RIESGO"
        if overall_score <= 60:
            return "RIESGO MEDIO"
        if overall_score <= 80:
            return "CONFIABLE"
        return "MUY CONFIABLE"

    def _build_verdict(self, risk_level: str, overall_score: int, liquidity_usd: float | None, volume_usd: float | None) -> str:
        liq = self._format_money(liquidity_usd)
        vol = self._format_money(volume_usd)
        return f"{risk_level} ({overall_score}/100). Liquidez {liq}, volumen 24h {vol}."

    def _build_analysis(self, risk_level: str, overall_score: int, liquidity_usd: float | None, volume_usd: float | None, market_cap: float | None, community_score: int, transparency_score: int, onchain_score: int, red_flags: list[str]) -> str:
        liq = self._format_money(liquidity_usd, fallback="no disponible")
        vol = self._format_money(volume_usd, fallback="no disponible")
        mc = self._format_money(market_cap, fallback="no disponible")
        red = "; ".join(red_flags[:3]) if red_flags else "sin red flags severas en esta corrida"
        return (
            f"El token quedó clasificado como {risk_level} con score {overall_score}/100 usando datos reales de DexScreener. "
            f"La liquidez observada es {liq}, el volumen de 24h es {vol} y el market cap/fdv ronda {mc}. "
            f"El componente de comunidad quedó ponderado por presencia de website y redes, mientras que transparencia se mantuvo conservadora "
            f"porque DexScreener no aporta auditorías ni identidad de equipo. El score onchain refleja principalmente antigüedad del par y relación entre liquidez y market cap. "
            f"Red flags principales: {red}. Esto sirve como filtro inicial, no como validación definitiva de seguridad o inversión."
        )

    def _format_money(self, value: float | None, fallback: str = "desconocido") -> str:
        if value is None:
            return fallback
        abs_value = abs(value)
        if 0 < abs_value < 0.01:
            return f"${value:.6f}".rstrip("0").rstrip(".")
        if abs_value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if abs_value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if abs_value >= 1_000:
            return f"${value / 1_000:.2f}K"
        return f"${value:.2f}"

    def _pair_age_hours(self, pair: dict) -> float | None:
        pair_created_at = self._to_float(pair.get("pairCreatedAt"))
        if pair_created_at is None:
            return None
        return max(0, (datetime.now(settings.timezone).timestamp() * 1000 - pair_created_at) / 3_600_000)

    def _format_launch_time(self, pair_created_at: float | None) -> str:
        if pair_created_at is None:
            return "—"
        return datetime.fromtimestamp(pair_created_at / 1000, tz=settings.timezone).strftime("%d/%m/%Y %H:%M:%S")

    def _format_launch_ago(self, pair_created_at: float | None) -> str:
        if pair_created_at is None:
            return "—"
        age_hours = max(0, (datetime.now(settings.timezone).timestamp() * 1000 - pair_created_at) / 3_600_000)
        if age_hours < 1:
            return f"hace {max(1, int(round(age_hours * 60)))} minutos"
        hours = int(age_hours)
        minutes = int(round((age_hours - hours) * 60))
        return f"hace {hours}h {minutes}m" if minutes > 0 else f"hace {hours} horas"

    def _build_projection(self, risk_level: str, overall_score: int, liquidity_usd: float | None, volume_usd: float | None) -> str:
        if liquidity_usd is None or volume_usd is None:
            return "Proyección incierta: faltan datos clave del mercado en esta corrida."
        if risk_level in {"SCAM", "ALTO RIESGO"}:
            return "Proyección especulativa y frágil: si se opera, sería solo como trade de altísimo riesgo, no como inversión."
        if overall_score >= 70:
            return "Proyección favorable a corto plazo si sostiene liquidez y actividad, pero sigue siendo un activo de riesgo alto."
        return "Proyección mixta: puede tener tracción de corto plazo, pero necesita confirmar liquidez, volumen y comunidad antes de ganar confianza."

    def _to_float(self, value) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
