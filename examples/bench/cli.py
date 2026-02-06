from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .harness import HarnessConfig, run_harness
from .schema import load_fixture_file


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic offline bench harness")
    parser.add_argument("--fixtures", type=Path, default=Path("examples/bench/fixtures/smoke.json"))
    parser.add_argument("--policy", type=str, default=None, help="Override policy path for all cases")
    parser.add_argument("--strategy", type=str, default=None, help="Override strategy for all cases")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after first failure")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write JSON report")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    fixtures = load_fixture_file(args.fixtures)

    config = HarnessConfig(
        seed=fixtures.seed if args.seed is None else args.seed,
        policy_path=args.policy,
        strategy=args.strategy,
        stop_on_failure=args.stop_on_failure,
    )
    result = run_harness(fixtures, config=config)
    report = json.dumps(result.to_dict(), indent=2)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
