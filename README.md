# scanner-launch

Repo base para el proyecto de scanner de lanzamientos crypto y detección de riesgo inicial en tokens nuevos.

## Archivo principal
- `CRYPTO_LAUNCH_SCANNER_SYSTEM_PROMPT.md`: prompt operativo del agente para discovery de tokens recién lanzados y análisis de riesgo.

## Objetivo
Construir un scanner que:
- encuentre tokens recién lanzados en tiempo real,
- devuelva JSON limpio y utilizable,
- priorice DexScreener, CoinGecko y fuentes verificables,
- y permita una capa posterior de scoring de riesgo DeFi.

## Estructura inicial
- `main.py`: entrypoint CLI.
- `src/scanner_launch/config.py`: configuración base.
- `src/scanner_launch/models.py`: schemas JSON y modelos.
- `src/scanner_launch/providers/search.py`: adapter de búsqueda.
- `src/scanner_launch/providers/extractors.py`: extractor de candidatos.
- `src/scanner_launch/services/discovery.py`: servicio de discovery.
- `src/scanner_launch/services/risk.py`: servicio de análisis de riesgo.
- `.env.example`: variables opcionales.
- `requirements.txt`: placeholder, sin dependencias externas obligatorias en este MVP.

## Estado actual
Esta versión ya tiene una primera fuente real conectada:
- corre por CLI,
- devuelve JSON estable,
- usa DexScreener como fuente pública de discovery,
- prioriza pares recientes,
- y sigue sin inventar datos faltantes.

Por ahora el discovery real sale de DexScreener. El análisis de riesgo ya usa datos reales del par en DexScreener para liquidez, volumen, comunidad básica y estructura del mercado, aunque sigue siendo conservador en transparencia porque no hay auditorías/equipo verificados en esta integración.

## Cómo correrlo
```bash
cd scanner-launch
python3 main.py discover
python3 main.py analyze BONK --chain solana
```

Cada corrida guarda snapshots JSON y CSV automáticos en `outputs/discover/...` o `outputs/analyze/...`.
Usá `--no-save` si no querés persistir esa ejecución.

## Ejemplos
### Discover
```bash
python3 main.py discover --limit 12 --max-age-hours 6
```

### Analyze
```bash
python3 main.py analyze WIF --chain solana
python3 main.py analyze BONK --chain solana
```

## Próximo paso recomendado
Expandir el scanner con más fuentes y persistencia:
- CoinGecko
- validación híbrida con búsqueda web + extracción por URL
- enriquecer scoring con más señales onchain/social y auditorías externas
- más afinado del análisis para tokens gigantes/multimercado
