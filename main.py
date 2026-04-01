import argparse
import sys

from phantom_snare.config import Config
from phantom_snare.deceptor import Deceptor
from phantom_snare.observer import Observer
from phantom_snare.shield import Shield
from phantom_snare.snare import Snare
from phantom_snare.sqlite_db import EvidenceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phantom_snare",
        description=(
            "Phantom-Snare HIDPS – honeypot + active-defence framework.\n"
            "Dashboard available at http://127.0.0.1:5000 after startup."
        ),
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Path to a JSON configuration file.",
    )
    parser.add_argument(
        "--ports",
        metavar="PORT",
        nargs="+",
        type=int,
        help="One or more TCP ports to listen on (overrides config file).",
    )
    parser.add_argument(
        "--bind",
        metavar="ADDRESS",
        default=None,
        help="Network interface to bind to (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--log-file",
        metavar="FILE",
        default=None,
        help="Write capture logs to this file (in addition to stderr).",
    )
    parser.add_argument(
        "--dashboard-port",
        metavar="PORT",
        type=int,
        default=None,
        help="Port for the Vault web dashboard (default: 5000).",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Disable the Vault web dashboard.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=True,
        help="Enable Flask debug mode on the Vault dashboard (default: on).",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable Flask debug mode on the Vault dashboard.",
    )
    parser.add_argument(
        "--dump-config",
        metavar="FILE",
        help="Write the effective configuration to FILE and exit.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config:
        try:
            config = Config.from_file(args.config)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading config: {exc}", file=sys.stderr)
            return 1
    else:
        config = Config()

    if args.ports:
        config.ports = args.ports
    if args.bind:
        config.bind_address = args.bind
    if args.log_file:
        config.log_file = args.log_file
    if args.dashboard_port:
        config.dashboard_port = args.dashboard_port
    if args.no_dashboard:
        config.dashboard_enabled = False

    dashboard_debug = not args.no_debug

    if args.dump_config:
        config.to_file(args.dump_config)
        print(f"Configuration written to {args.dump_config}")
        return 0

    store = EvidenceStore(db_path=config.evidence_db)
    store.connect()

    shield = Shield(
        evidence_store=store,
        max_connections_per_minute=config.max_connections_per_minute,
    )

    deceptor = Deceptor(evidence_store=store)

    observer = Observer(
        evidence_store=store,
        shield=shield,
        deceptor=deceptor,
    )

    snare = Snare(
        config=config,
        shield=shield,
        deceptor=deceptor,
        on_capture=observer.on_capture,
    )

    vault = None
    if config.dashboard_enabled:
        try:
            from phantom_snare.vault import Vault
            vault = Vault(
                evidence_store=store,
                shield=shield,
                observer=observer,
                deceptor=deceptor,
                host=config.dashboard_host,
                port=config.dashboard_port,
                debug=dashboard_debug,
            )
            vault.start()
            print(
                f"[phantom_snare] Dashboard: http://{config.dashboard_host}:{config.dashboard_port}",
                file=sys.stderr,
            )
        except RuntimeError as exc:
            print(f"[phantom_snare] Dashboard disabled: {exc}", file=sys.stderr)

    try:
        snare.run_forever()
    finally:
        store.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
