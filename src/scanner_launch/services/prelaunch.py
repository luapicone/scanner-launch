from __future__ import annotations

from datetime import datetime

from scanner_launch.buy_links import build_prelaunch_buy_target
from scanner_launch.config import settings
from scanner_launch.models import PrelaunchProject, PrelaunchResult, now_art
from scanner_launch.providers.prelaunch import PrelaunchProvider


class PrelaunchService:
    def __init__(self, provider: PrelaunchProvider | None = None) -> None:
        self.provider = provider or PrelaunchProvider()

    def scan(self, limit: int = 40, min_score: int = 60, future_only: bool = True, source_limit: int | None = None) -> PrelaunchResult:
        fetch_limit = max(limit * 4, 120, source_limit or 0)
        projects, warnings = self.provider.fetch_projects(limit=fetch_limit)
        enriched = [self._score_project(project) for project in projects]
        if future_only:
            enriched = [item for item in enriched if self._launch_timestamp(item.launchTime) is None or self._launch_timestamp(item.launchTime) >= datetime.now(settings.timezone).timestamp()]
        enriched = [item for item in enriched if item.overallScore >= min_score]
        enriched.sort(key=lambda item: (self._launch_timestamp(item.launchTime) or 10**18, -item.overallScore, item.name.lower()))
        return PrelaunchResult(
            projects=enriched[:limit],
            source="ICO Analytics + CoinMarketCap Upcoming",
            fetchedAt=now_art(datetime.now(settings.timezone)),
            warnings=warnings,
        )

    def _score_project(self, project: dict) -> PrelaunchProject:
        legitimacy = self._score_legitimacy(project)
        readiness = self._score_readiness(project)
        hype = self._score_hype(project)
        access = self._score_access(project)
        overall = round(legitimacy * 0.35 + readiness * 0.25 + hype * 0.20 + access * 0.20)
        risk_level = self._risk_level(overall)
        red_flags, green_flags = self._flags(project, legitimacy, readiness, access)
        projection = self._projection(overall, legitimacy, readiness, project)
        buy_verdict = self._buy_verdict(overall, legitimacy, access, risk_level)
        analysis = self._analysis(project, legitimacy, readiness, hype, access, overall, risk_level)

        launch_time = self._format_launch_time(project.get("launch_ts"), project.get("launchText"))
        launch_ago = self._format_launch_ago(project.get("launch_ts"))
        buy_target = build_prelaunch_buy_target(
            project.get("buyUrl"),
            project.get("websiteUrl"),
            project.get("projectUrl"),
            project.get("stage"),
        )
        buy_link = str(buy_target.get("buyLink") or "—")
        buy_label = str(buy_target.get("buyLabel") or ("Comprar / participar" if project.get("buyUrl") else "Ver proyecto"))
        buy_where = str(buy_target.get("buyWhere") or "—")
        buy_note = str(buy_target.get("buyNote") or "—")
        buy_platform = [project.get("source") or "—"]
        if project.get("stage"):
            buy_platform.append(project.get("stage"))

        return PrelaunchProject(
            id=project.get("id") or "—",
            name=project.get("name") or "—",
            symbol=project.get("symbol") or "—",
            source=project.get("source") or "—",
            sourceUrl=project.get("sourceUrl") or "—",
            projectUrl=project.get("projectUrl") or "—",
            chain=project.get("chain") or "—",
            stage=project.get("stage") or "—",
            launchTime=launch_time,
            launchAgo=launch_ago,
            websiteUrl=project.get("websiteUrl") or "—",
            twitterUrl=project.get("twitterUrl") or "—",
            telegramUrl=project.get("telegramUrl") or "—",
            docsUrl=project.get("docsUrl") or "—",
            buyPlatform=buy_platform,
            buyLink=buy_link,
            buyWhere=buy_where,
            buyLabel=buy_label,
            buyNote=buy_note,
            hasDirectBuy=bool(buy_target.get("hasDirectBuy")),
            categories=project.get("categories") or [],
            investorsCount=project.get("investorsCount"),
            fundingUsd=project.get("fundingUsd") or "—",
            scores={
                "legitimidad": legitimacy,
                "readiness": readiness,
                "hype": hype,
                "access": access,
            },
            overallScore=overall,
            riskLevel=risk_level,
            redFlags=red_flags,
            greenFlags=green_flags,
            projection=projection,
            buyVerdict=buy_verdict,
            analysis=analysis,
            fetchedAt=now_art(datetime.now(settings.timezone)),
        )

    def _score_legitimacy(self, project: dict) -> int:
        score = 15
        if project.get("websiteUrl"):
            score += 20
        if project.get("docsUrl"):
            score += 15
        if project.get("twitterUrl"):
            score += 10
        if project.get("telegramUrl"):
            score += 10
        investors = project.get("investorsCount")
        if investors:
            score += min(20, investors * 3)
        if project.get("source") == "ICO Analytics":
            score += 10
        if not project.get("websiteUrl") and not project.get("docsUrl"):
            score -= 15
        return max(0, min(100, score))

    def _score_readiness(self, project: dict) -> int:
        score = 10
        launch_ts = project.get("launch_ts")
        if launch_ts:
            score += 35
            hours = max(0, (launch_ts - datetime.now(settings.timezone).timestamp() * 1000) / 3_600_000)
            if hours <= 72:
                score += 25
            elif hours <= 24 * 14:
                score += 18
            elif hours <= 24 * 60:
                score += 10
        elif any(word in (project.get("launchText") or "").lower() for word in ["q", "half", "end of", "month"]):
            score += 12

        stage = (project.get("stage") or "").lower()
        if "tge" in stage:
            score += 15
        elif "auction" in stage or "sale" in stage:
            score += 18
        elif "mainnet" in stage or "listing" in stage:
            score += 10
        return max(0, min(100, score))

    def _score_hype(self, project: dict) -> int:
        score = 10
        funding = project.get("fundingValue")
        if funding:
            if funding >= 50_000_000:
                score += 35
            elif funding >= 10_000_000:
                score += 25
            elif funding >= 1_000_000:
                score += 15
        categories = {cat.lower() for cat in (project.get("categories") or [])}
        if categories & {"ai", "depin", "solana ecosystem", "base ecosystem", "zero-knowledge", "infrastructure"}:
            score += 15
        if project.get("twitterUrl") and project.get("telegramUrl"):
            score += 20
        elif project.get("twitterUrl") or project.get("telegramUrl"):
            score += 10
        return max(0, min(100, score))

    def _score_access(self, project: dict) -> int:
        score = 5
        if project.get("buyUrl"):
            score += 35
        elif project.get("websiteUrl"):
            score += 25
        if project.get("projectUrl"):
            score += 15
        if project.get("docsUrl"):
            score += 10
        stage = (project.get("stage") or "").lower()
        if any(word in stage for word in ["auction", "sale", "tge"]):
            score += 20
        return max(0, min(100, score))

    def _risk_level(self, overall: int) -> str:
        if overall >= 75:
            return "INTERESANTE"
        if overall >= 60:
            return "SEGUIR"
        if overall >= 45:
            return "CAUTELA"
        if overall >= 25:
            return "ALTO RIESGO"
        return "EVITAR"

    def _flags(self, project: dict, legitimacy: int, readiness: int, access: int) -> tuple[list[str], list[str]]:
        red_flags: list[str] = []
        green_flags: list[str] = []

        if not project.get("websiteUrl"):
            red_flags.append("Sin website o landing verificable")
        else:
            green_flags.append("Tiene website o landing")
        if project.get("buyUrl"):
            green_flags.append("Tiene ruta directa de entrada o participación")
        if not project.get("docsUrl"):
            red_flags.append("Sin whitepaper/docs detectables")
        else:
            green_flags.append("Tiene docs o whitepaper")
        if project.get("twitterUrl"):
            green_flags.append("Tiene Twitter/X")
        if project.get("telegramUrl"):
            green_flags.append("Tiene Telegram")
        if project.get("investorsCount"):
            green_flags.append(f"Muestra {project.get('investorsCount')} inversores/fondos listados")
        if project.get("fundingValue") and project.get("fundingValue") >= 10_000_000:
            green_flags.append("Funding relevante reportado")
        if readiness < 35:
            red_flags.append("Fecha o ventana de lanzamiento poco precisa")
        if access < 35:
            red_flags.append("Ruta de acceso a prelanzamiento poco clara")
        if legitimacy < 40:
            red_flags.append("Legitimidad documental baja para un prelaunch")

        return list(dict.fromkeys(red_flags)), list(dict.fromkeys(green_flags))

    def _projection(self, overall: int, legitimacy: int, readiness: int, project: dict) -> str:
        if overall >= 75:
            return "Proyección pre-launch fuerte: buen setup para seguimiento cercano del listing, siempre con gestión de riesgo dura."
        if overall >= 60:
            return "Proyección positiva moderada: puede captar atención en el lanzamiento, pero necesita ejecución prolija y confirmación final."
        if overall >= 45:
            return "Proyección mixta: hay señales interesantes, pero todavía falta convicción para una entrada pre-launch agresiva."
        return "Proyección débil o demasiado incierta: no parece una oportunidad limpia para buscar flip en listing."

    def _buy_verdict(self, overall: int, legitimacy: int, access: int, risk_level: str) -> str:
        if overall >= 70 and legitimacy >= 60 and access >= 50:
            return "Podría convenir vigilar el prelanzamiento con checklist estricta, tamaño chico y salida definida antes del listing."
        if overall >= 50:
            return "Solo watchlist y validación adicional. No conviene comprar ciegamente el prelanzamiento."
        if risk_level in {"ALTO RIESGO", "EVITAR"}:
            return "No conviene comprar prelanzamiento con la evidencia actual."
        return "No hay suficiente señal para recomendar entrada pre-launch."

    def _analysis(self, project: dict, legitimacy: int, readiness: int, hype: int, access: int, overall: int, risk_level: str) -> str:
        launch_text = self._format_launch_time(project.get("launch_ts"), project.get("launchText"))
        categories = ", ".join(project.get("categories") or []) or "sin categorías claras"
        funding = project.get("fundingUsd") or "—"
        return (
            f"Proyecto pre-launch evaluado desde {project.get('source')}. Lanzamiento estimado: {launch_text}. "
            f"Stage: {project.get('stage') or '—'}. Categorías: {categories}. Funding reportado: {funding}. "
            f"Legitimidad {legitimacy}/100, readiness {readiness}/100, hype {hype}/100 y acceso {access}/100. "
            f"Resultado global {overall}/100, clasificado como {risk_level}. Esta señal sirve para filtrar oportunidades pre-listing, no garantiza rendimiento ni seguridad del trade."
        )

    def _format_launch_time(self, launch_ts: int | None, launch_text: str | None) -> str:
        if launch_ts:
            return datetime.fromtimestamp(launch_ts / 1000, tz=settings.timezone).strftime("%d/%m/%Y %H:%M:%S")
        return launch_text or "—"

    def _format_launch_ago(self, launch_ts: int | None) -> str:
        if not launch_ts:
            return "—"
        delta_ms = launch_ts - datetime.now(settings.timezone).timestamp() * 1000
        hours = delta_ms / 3_600_000
        if hours < 0:
            return "fecha pasada o inmediata"
        if hours < 1:
            return f"en {max(1, int(round(hours * 60)))} minutos"
        whole_hours = int(hours)
        minutes = int(round((hours - whole_hours) * 60))
        return f"en {whole_hours}h {minutes}m" if minutes > 0 else f"en {whole_hours} horas"

    def _launch_timestamp(self, launch_time: str | None) -> float | None:
        if not launch_time:
            return None
        try:
            return datetime.strptime(launch_time, "%d/%m/%Y %H:%M:%S").replace(tzinfo=settings.timezone).timestamp()
        except ValueError:
            return None
