from __future__ import annotations

from urllib.parse import urlparse

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
                "buyNote": f"Ruta directa detectada para el ecosistema {dex_label}.",
                "hasDirectBuy": True,
            }
        return {
            "buyWhere": f"Jupiter · {chain_label}",
            "buyLink": f"https://jup.ag/swap/SOL-{token}",
            "buyLabel": "Comprar en Jupiter",
            "buyNote": f"Swap directo sugerido para {chain_label}. Mercado base detectado en {dex_label}.",
            "hasDirectBuy": True,
        }

    if chain in UNISWAP_CHAIN_PARAMS and token:
        chain_param = UNISWAP_CHAIN_PARAMS[chain]
        return {
            "buyWhere": f"Uniswap · {chain_label}",
            "buyLink": f"https://app.uniswap.org/swap?chain={chain_param}&outputCurrency={token}",
            "buyLabel": "Comprar en Uniswap",
            "buyNote": f"Ruta directa sugerida para {chain_label}. Mercado detectado en {dex_label}.",
            "hasDirectBuy": True,
        }

    if chain in {"bsc", "bnb"} and token:
        return {
            "buyWhere": f"PancakeSwap · {chain_label}",
            "buyLink": f"https://pancakeswap.finance/swap?chain=bsc&outputCurrency={token}",
            "buyLabel": "Comprar en PancakeSwap",
            "buyNote": f"Ruta directa sugerida para {chain_label}. Mercado detectado en {dex_label}.",
            "hasDirectBuy": True,
        }

    if chain in {"avalanche", "avax"} and token:
        return {
            "buyWhere": f"Trader Joe · {chain_label}",
            "buyLink": f"https://www.traderjoexyz.com/avalanche/trade?outputCurrency={token}",
            "buyLabel": "Comprar en Trader Joe",
            "buyNote": f"Ruta directa sugerida para {chain_label}. Mercado detectado en {dex_label}.",
            "hasDirectBuy": True,
        }

    if market_url and market_url != "—":
        return {
            "buyWhere": f"{dex_label} · {chain_label}",
            "buyLink": market_url,
            "buyLabel": f"Abrir mercado en {dex_label}",
            "buyNote": "No encontré una ruta de swap universal confiable para esta chain, así que dejo el mercado detectado.",
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
        return {
            "buyWhere": f"{venue} · {stage or 'Prelaunch'}",
            "buyLink": buy_url,
            "buyLabel": f"Entrar por {venue}",
            "buyNote": "Se detectó una ruta pública de entrada o participación desde la fuente relevada.",
            "hasDirectBuy": True,
        }

    if website_url and website_url != "—":
        venue = domain_label(website_url)
        return {
            "buyWhere": f"{venue} · sitio oficial",
            "buyLink": website_url,
            "buyLabel": "Ir al sitio oficial",
            "buyNote": "Todavía no detecté una compra pública directa. El acceso queda referenciado al sitio oficial del proyecto.",
            "hasDirectBuy": False,
        }

    if project_url and project_url != "—":
        venue = domain_label(project_url)
        return {
            "buyWhere": f"{venue} · fuente",
            "buyLink": project_url,
            "buyLabel": "Abrir fuente",
            "buyNote": "No encontré una ruta clara de compra y dejo la fuente original para seguimiento manual.",
            "hasDirectBuy": False,
        }

    return {
        "buyWhere": "Compra no detectada",
        "buyLink": "—",
        "buyLabel": "Sin ruta",
        "buyNote": "No encontré una ruta pública de compra o participación en esta corrida.",
        "hasDirectBuy": False,
    }
