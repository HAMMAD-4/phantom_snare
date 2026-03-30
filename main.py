#!/usr/bin/env python3
"""phantom_snare – CLI entry point."""

import argparse
import sys

from phantom_snare.config import Config
from phantom_snare.snare import Snare


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phantom_snare",
        description="A lightweight network honeypot that captures intrusion attempts.",
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
        help="Write capture logs to this file (in addition to stdout).",
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

    # Load config from file or use defaults
    if args.config:
        try:
            config = Config.from_file(args.config)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading config: {exc}", file=sys.stderr)
            return 1
    else:
        config = Config()

    # CLI overrides
    if args.ports:
        config.ports = args.ports
    if args.bind:
        config.bind_address = args.bind
    if args.log_file:
        config.log_file = args.log_file

    if args.dump_config:
        config.to_file(args.dump_config)
        print(f"Configuration written to {args.dump_config}")
        return 0

    snare = Snare(config)
    snare.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
