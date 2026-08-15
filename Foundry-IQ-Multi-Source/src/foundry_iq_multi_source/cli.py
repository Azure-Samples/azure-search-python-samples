from __future__ import annotations

import argparse
import json
import sys

from .config import DEFAULT_QUERY, Settings
from .sample import MultiSourceSample


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a Foundry IQ query across a Search index and an external MCP "
            "server."
        )
    )
    parser.add_argument(
        "action",
        choices=["run", "setup", "query", "cleanup"],
        nargs="?",
        default="run",
    )
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument(
        "--keep-resources",
        action="store_true",
        help="Keep resources after the run action for inspection.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    sample = MultiSourceSample(settings, settings.search_credential())
    operation_failed = False
    try:
        if args.action in {"run", "setup"}:
            sample.setup()
            print("Created the index, both knowledge sources, and knowledge base.")
        if args.action in {"run", "query"}:
            answer, evidence = sample.query(args.query)
            print("\nSynthesized answer\n------------------")
            print(answer)
            print("\nDual-source evidence\n--------------------")
            print(json.dumps(evidence.as_dict(), indent=2))
            print(f"\nFull response: {settings.output_path}")
        if args.action == "cleanup":
            sample.cleanup()
            print("Deleted all sample resources.")
    except Exception:
        operation_failed = True
        raise
    finally:
        if args.action == "run" and not args.keep_resources:
            try:
                sample.cleanup()
                print("Deleted all sample resources.")
            except Exception as cleanup_error:
                if operation_failed:
                    print(
                        f"Cleanup also failed: {cleanup_error}",
                        file=sys.stderr,
                    )
                else:
                    raise
            finally:
                sample.close()
        else:
            sample.close()
