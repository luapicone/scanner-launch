# scanner-launch

Repo base para el proyecto de scanner de lanzamientos crypto, detección de riesgo inicial en tokens nuevos y análisis pre-launch de proyectos todavía no listados.

## Archivo principal
- `CRYPTO_LAUNCH_SCANNER_SYSTEM_PROMPT.md`: prompt operativo del agente para discovery de tokens recién lanzados y análisis de riesgo.

## Objetivo
Construir un scanner que:
- encuentre tokens recién lanzados en tiempo real,
- detecte proyectos próximos a TGE/listing antes del lanzamiento,
- devuelva JSON limpio y utilizable,
- priorice fuentes verificables,
- y permita una capa posterior de scoring heurístico y riesgo.

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
Esta versión ya tiene dos líneas reales de trabajo conectadas:

### 1. Tokens ya lanzados
- corre por CLI,
- devuelve JSON estable,
- usa DexScreener como fuente pública de discovery,
- prioriza pares recientes,
- y sigue sin inventar datos faltantes.

### 2. Proyectos pre-launch
- usa fuentes públicas parseables de upcoming launches,
- hoy integra `ICO Analytics` y `CoinMarketCap Upcoming`,
- estima fecha/stage de lanzamiento,
- arma un scoring heurístico de legitimidad, readiness, hype y acceso,
- detecta dónde comprar o entrar exactamente cuando la fuente o la chain permiten resolverlo,
- cuando no hay compra pública directa detectable, cae honestamente al sitio oficial o a la fuente original,
- y devuelve una señal operativa tipo `INTERESANTE / SEGUIR / CAUTELA / EVITAR`.

Importante: el modo prelaunch no promete rentabilidad ni “predice” el listing. Sirve para filtrar mejor oportunidades previas al lanzamiento con evidencia pública verificable.

## Cómo correrlo
```bash
cd scanner-launch
python3 main.py discover
python3 main.py analyze BONK --chain solana
python3 main.py scan --limit 20 --max-age-hours 24
python3 main.py prelaunch --limit 40
python3 main.py web --port 8765
```

Cada corrida guarda snapshots JSON y CSV automáticos en `outputs/discover/...`, `outputs/analyze/...`, `outputs/scan/...` o `outputs/prelaunch/...`.
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

### Scan completo de la corrida
```bash
python3 main.py scan --limit 20 --max-age-hours 24
```

### Prelaunch real
```bash
python3 main.py prelaunch --limit 40
```

### Dashboard HTML local
```bash
python3 main.py web --port 8765
```
Después abrís:
```bash
http://127.0.0.1:8765
```
Y en la UI elegís el modo `Prelaunch real` para ver:
- cuándo sería el lanzamiento,
- qué tan confiable parece el proyecto,
- si conviene solo watchlist o podría valer la pena seguir el prelanzamiento,
- la proyección heurística del listing,
- una sección explícita de **dónde comprar**,
- un botón directo a la ruta de compra/participación cuando se puede resolver,
- o un fallback honesto al sitio oficial/fuente cuando todavía no hay compra pública detectada.

## Próximo paso recomendado
Expandir el scanner con más fuentes y persistencia:
- CoinGecko para enriquecer metadata post-listing
- launchpads / ICO calendars extra para upcoming tokens
- validación híbrida con búsqueda web + extracción por URL
- enriquecer scoring con más señales onchain/social y auditorías externas
