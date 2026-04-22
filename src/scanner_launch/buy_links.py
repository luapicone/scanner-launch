from __future__ import annotations

from urllib.parse import urlparse


def _steps(*items: str) -> str:
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(items, start=1) if item)

DEX_LABELS = {
    "pumpfun": "Pump.fun",
    "pumpswap": "PumpSwap",
    "raydium": "Raydium",
    "orca": "Orca",
    "meteora": "Meteora",
    "uniswap": "Uniswap",
    "aerodrome": "Aerodrome",
    "pancakeswap": "PancakeSwap",
    "traderjoe": "Trader Joe",
    "spookyswap": "SpookySwap",
    "sushiswap": "SushiSwap",
}

CHAIN_LABELS = {
    "solana": "Solana",
    "ethereum": "Ethereum",
    "eth": "Ethereum",
    "base": "Base",
    "arbitrum": "Arbitrum",
    "polygon": "Polygon",
    "bsc": "BNB Chain",
    "bnb": "BNB Chain",
    "avalanche": "Avalanche",
    "avax": "Avalanche",
    "optimism": "Optimism",
}

UNISWAP_CHAIN_PARAMS = {
    "ethereum": "ethereum",
    "eth": "ethereum",
    "base": "base",
    "arbitrum": "arbitrum",
    "polygon": "polygon",
    "optimism": "optimism",
}


def prettify_dex(dex_id: str | None) -> str:
    key = (dex_id or "").strip().lower()
    return DEX_LABELS.get(key, dex_id or "Mercado detectado")


def prettify_chain(chain_id: str | None) -> str:
    key = (chain_id or "").strip().lower()
    return CHAIN_LABELS.get(key, chain_id or "—")


def domain_label(url: str | None) -> str:
    if not url or url == "—":
        return "Ruta no detectada"
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return "Ruta no detectada"

    host = host.removeprefix("www.")
    known = {
        "jup.ag": "Jupiter",
        "pump.fun": "Pump.fun",
        "app.uniswap.org": "Uniswap",
        "pancakeswap.finance": "PancakeSwap",
        "traderjoexyz.com": "Trader Joe",
        "impossible.finance": "Impossible Finance",
        "blog.impossible.finance": "Impossible Finance",
        "coinlist.co": "CoinList",
        "bybit.com": "Bybit",
        "gate.io": "Gate.io",
        "kucoin.com": "KuCoin",
        "binance.com": "Binance",
        "raydium.io": "Raydium",
        "orca.so": "Orca",
    }
    if host in known:
        return known[host]
    parts = [part for part in host.split(".") if part and part not in {"com", "io", "finance", "org", "xyz", "app", "net", "gg"}]
    if not parts:
        return host or "Ruta detectada"
    return " ".join(part.capitalize() for part in parts[:2])


def build_live_buy_target(chain_id: str | None, token_address: str | None, dex_id: str | None, market_url: str | None) -> dict[str, str | bool]:
    chain = (chain_id or "").strip().lower()
    token = (token_address or "").strip()
    dex_label = prettify_dex(dex_id)
    chain_label = prettify_chain(chain_id)

    if chain == "solana" and token:
        if (dex_id or "").strip().lower() in {"pumpfun", "pumpswap"} or token.endswith("pump"):
            return {
                "buyWhere": f"{dex_label} · {chain_label}",
                "buyLink": f"https://pump.fun/coin/{token}",
                "buyLabel": f"Comprar en {dex_label}",
                "buyNote": _steps(
                    f"Abrí {dex_label} desde el botón.",
                    "Conectá tu wallet.",
                    "Verificá que el token y la red sean correctos.",
                    "Elegí el monto y confirmá la compra.",
                ),
                "hasDirectBuy": True,
            }
        return {
            "buyWhere": f"Jupiter · {chain_label}",
            "buyLink": f"https://jup.ag/swap/SOL-{token}",
            "buyLabel": "Comprar en Jupiter",
            "buyNote": _steps(
                "Abrí Jupiter desde el botón.",
                f"Operá en la red {chain_label} con tu wallet conectada.",
                "Revisá el token de salida y el slippage antes de confirmar.",
                "Confirmá el swap para conseguir el token.",
            ),
            "hasDirectBuy": True,
        }

    if chain in UNISWAP_CHAIN_PARAMS and token:
        chain_param = UNISWAP_CHAIN_PARAMS[chain]
        return {
            "buyWhere": f"Uniswap · {chain_label}",
            "buyLink": f"https://app.uniswap.org/swap?chain={chain_param}&outputCurrency={token}",
            "buyLabel": "Comprar en Uniswap",
            "buyNote": _steps(
                "Abrí Uniswap desde el botón.",
                f"Conectá tu wallet en {chain_label}.",
                "Verificá contrato, red y liquidez.",
                "Confirmá el swap para comprar el token.",
            ),
            "hasDirectBuy": True,
        }

    if chain in {"bsc", "bnb"} and token:
        return {
            "buyWhere": f"PancakeSwap · {chain_label}",
            "buyLink": f"https://pancakeswap.finance/swap?chain=bsc&outputCurrency={token}",
            "buyLabel": "Comprar en PancakeSwap",
            "buyNote": _steps(
                "Abrí PancakeSwap desde el botón.",
                f"Conectá tu wallet en {chain_label}.",
                "Verificá contrato, par y slippage.",
                "Confirmá el swap para conseguir el token.",
            ),
            "hasDirectBuy": True,
        }

    if chain in {"avalanche", "avax"} and token:
        return {
            "buyWhere": f"Trader Joe · {chain_label}",
            "buyLink": f"https://www.traderjoexyz.com/avalanche/trade?outputCurrency={token}",
            "buyLabel": "Comprar en Trader Joe",
            "buyNote": _steps(
                "Abrí Trader Joe desde el botón.",
                f"Conectá tu wallet en {chain_label}.",
                "Verificá contrato, pool y liquidez antes de operar.",
                "Confirmá el swap para conseguir el token.",
            ),
            "hasDirectBuy": True,
        }

    if market_url and market_url != "—":
        return {
            "buyWhere": f"{dex_label} · {chain_label}",
            "buyLink": market_url,
            "buyLabel": f"Abrir mercado en {dex_label}",
            "buyNote": _steps(
                f"Abrí el mercado detectado en {dex_label} desde el botón.",
                "Revisá si el proyecto publica ahí el par o la ruta de compra.",
                "Verificá contrato, red y liquidez antes de operar.",
                "Si no aparece compra directa, seguí las redes oficiales del proyecto.",
            ),
            "hasDirectBuy": False,
        }

    return {
        "buyWhere": f"{dex_label} · {chain_label}",
        "buyLink": "—",
        "buyLabel": "Ruta no detectada",
        "buyNote": "No pude detectar una ruta concreta de compra en esta corrida.",
        "hasDirectBuy": False,
    }


def build_prelaunch_buy_target(buy_url: str | None, website_url: str | None, project_url: str | None, stage: str | None) -> dict[str, str | bool]:
    if buy_url and buy_url != "—":
        venue = domain_label(buy_url)
        low = buy_url.lower()
        if any(token in low for token in ["whitelist", "waitlist", "register", "join", "invite"]):
            return {
                "buyWhere": f"{venue} · acceso temprano",
                "buyLink": buy_url,
                "buyLabel": "Registrarse / Whitelist",
                "buyNote": _steps(
                    f"Abrí {venue} desde el botón.",
                    "Completá el registro, whitelist o waitlist que figure en la página.",
                    "Seguí las instrucciones del proyecto para quedar habilitado.",
                    "Revisá luego email, Discord o Telegram para saber cuándo reclamar o comprar.",
                ),
                "hasDirectBuy": False,
            }
        if any(token in low for token in ["tge", "listing", "launch", "update", "guide", "claim", "airdrop"]):
            return {
                "buyWhere": f"{venue} · guía de acceso",
                "buyLink": buy_url,
                "buyLabel": "Cómo conseguirlo",
                "buyNote": _steps(
                    f"Abrí la guía o actualización en {venue} desde el botón.",
                    "Leé cómo se distribuye el token: claim, TGE, airdrop, listing o registro previo.",
                    "Seguí exactamente las instrucciones oficiales que indique el proyecto.",
                    "Usá Twitter, Telegram o Discord oficiales para validar fecha y modalidad antes de moverte.",
                ),
                "hasDirectBuy": False,
            }
        return {
            "buyWhere": f"{venue} · {stage or 'Prelaunch'}",
            "buyLink": buy_url,
            "buyLabel": f"Entrar por {venue}",
            "buyNote": _steps(
                f"Abrí {venue} desde el botón.",
                "Revisá si la página ofrece compra, registro, claim o participación.",
                "Confirmá que sea la ruta oficial del proyecto.",
                "Seguí los pasos publicados ahí para conseguir el token.",
            ),
            "hasDirectBuy": True,
        }

    if website_url and website_url != "—":
        venue = domain_label(website_url)
        return {
            "buyWhere": f"{venue} · sitio oficial",
            "buyLink": website_url,
            "buyLabel": "Ir al sitio oficial",
            "buyNote": _steps(
                f"Abrí el sitio oficial de {venue} desde el botón.",
                "Buscá secciones como token, TGE, claim, whitelist, launch, docs o community.",
                "Entrá a los canales oficiales del proyecto para ver cómo se consigue el token.",
                "No operes hasta confirmar la modalidad oficial de distribución.",
            ),
            "hasDirectBuy": False,
        }

    if project_url and project_url != "—":
        venue = domain_label(project_url)
        return {
            "buyWhere": f"{venue} · fuente",
            "buyLink": project_url,
            "buyLabel": "Abrir fuente",
            "buyNote": _steps(
                "Abrí la fuente original desde el botón.",
                "Revisá links oficiales del proyecto, docs y redes.",
                "Buscá si la distribución será por claim, whitelist, launchpad o listing.",
                "Usá esa info para ir a la ruta oficial antes de intentar comprar.",
            ),
            "hasDirectBuy": False,
        }

    return {
        "buyWhere": "Compra no detectada",
        "buyLink": "—",
        "buyLabel": "Sin ruta",
        "buyNote": "No encontré una ruta pública de compra o participación en esta corrida.",
        "hasDirectBuy": False,
    }
