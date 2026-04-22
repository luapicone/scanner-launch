from __future__ import annotations

import argparse
import json

from scanner_launch.models import to_dict
from scanner_launch.services.discovery import DiscoveryService
from scanner_launch.services.risk import RiskAnalyzerService
from scanner_launch.services.scan import BatchScanService
from scanner_launch.services.prelaunch import PrelaunchService
from scanner_launch.storage import SnapshotStore
from scanner_launch.webapp import serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crypto launch scanner MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="Buscar tokens recién lanzados")
    discover.add_argument("--limit", type=int, default=12, help="Cantidad máxima de tokens buscados")
    discover.add_argument("--max-age-hours", type=int, default=6, help="Ventana de lanzamiento prioritaria")
    discover.add_argument("--no-save", action="store_true", help="No guardar snapshot JSON de esta corrida")

    analyze = subparsers.add_parser("analyze", help="Analizar riesgo de un token")
    analyze.add_argument("token", help="Nombre o símbolo del token")
    analyze.add_argument("--chain", help="Blockchain sugerida", default=None)
    analyze.add_argument("--no-save", action="store_true", help="No guardar snapshot JSON de esta corrida")

    scan = subparsers.add_parser("scan", help="Descubrir y evaluar todos los tokens de la corrida")
    scan.add_argument("--limit", type=int, default=20, help="Cantidad máxima de tokens a evaluar")
    scan.add_argument("--max-age-hours", type=int, default=24, help="Ventana máxima de lanzamiento")
    scan.add_argument("--no-save", action="store_true", help="No guardar snapshot JSON/CSV de esta corrida")

    prelaunch = subparsers.add_parser("prelaunch", help="Analizar proyectos previos al lanzamiento")
    prelaunch.add_argument("--limit", type=int, default=40, help="Cantidad máxima de proyectos a evaluar")
    prelaunch.add_argument("--no-save", action="store_true", help="No guardar snapshot JSON/CSV de esta corrida")

    web = subparsers.add_parser("web", help="Levantar dashboard HTML local")
    web.add_argument("--host", default="127.0.0.1", help="Host para servir la web")
    web.add_argument("--port", type=int, default=8765, help="Puerto para servir la web")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    store = SnapshotStore()

    if args.command == "discover":
        result = DiscoveryService().discover(limit=args.limit, max_age_hours=args.max_age_hours)
        payload = to_dict(result)
        if not args.no_save:
            snapshot_json_path, snapshot_csv_path = store.save("discover", result)
            payload["snapshotPath"] = str(snapshot_json_path)
            payload["snapshotCsvPath"] = str(snapshot_csv_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "analyze":
        result = RiskAnalyzerService().analyze(token=args.token, chain=args.chain)
        payload = to_dict(result)
        if not args.no_save:
            snapshot_json_path, snapshot_csv_path = store.save("analyze", result)
            payload["snapshotPath"] = str(snapshot_json_path)
            payload["snapshotCsvPath"] = str(snapshot_csv_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "scan":
        result = BatchScanService().scan(limit=args.limit, max_age_hours=args.max_age_hours)
        payload = to_dict(result)
        if not args.no_save:
            snapshot_json_path, snapshot_csv_path = store.save("scan", result)
            payload["snapshotPath"] = str(snapshot_json_path)
            payload["snapshotCsvPath"] = str(snapshot_csv_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "prelaunch":
        result = PrelaunchService().scan(limit=args.limit)
        payload = to_dict(result)
        if not args.no_save:
            snapshot_json_path, snapshot_csv_path = store.save("prelaunch", result)
            payload["snapshotPath"] = str(snapshot_json_path)
            payload["snapshotCsvPath"] = str(snapshot_csv_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "web":
        serve(host=args.host, port=args.port)
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
