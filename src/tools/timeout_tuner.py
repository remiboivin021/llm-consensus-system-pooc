from __future__ import annotations

"""
Offline helper to suggest provider/e2e timeouts from latency samples.

Usage:
    python -m src.tools.timeout_tuner --input latencies.csv --format csv

CSV expectations:
    - Header row optional.
    - Column named latency_ms OR first column is latency in milliseconds.

JSON expectations:
    - Either array of numbers, or array of objects with latency_ms field.

No external dependencies; deterministic outputs.
"""

import argparse
import csv
import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable, List


@dataclass
class TimeoutSuggestion:
    provider_timeout_ms: int
    e2e_timeout_ms: int
    percentile_used: float
    percentile_value_ms: float
    sample_count: int
    warnings: List[str]


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        raise ValueError("No latency samples provided")
    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be in (0,1]")
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    idx = ceil(percentile * (len(sorted_vals) - 1))
    return float(sorted_vals[idx])


def suggest_timeouts(
    latencies_ms: Iterable[float],
    *,
    percentile: float = 0.95,
    safety_margin: float = 1.2,
    overhead_ms: int = 200,
    provider_min_ms: int = 500,
    provider_max_ms: int = 20000,
    e2e_multiplier: float = 2.0,
    e2e_max_ms: int = 60000,
    min_samples_warn: int = 30,
) -> TimeoutSuggestion:
    values = [float(v) for v in latencies_ms if v is not None]
    if not values:
        raise ValueError("No latency samples provided")

    warnings: List[str] = []
    if len(values) < min_samples_warn:
        warnings.append(f"low_sample_count:{len(values)}")

    p_val = _percentile(values, percentile)
    provider_raw = p_val * safety_margin + overhead_ms
    provider_timeout = int(max(provider_min_ms, min(provider_raw, provider_max_ms)))

    e2e_raw = provider_timeout * e2e_multiplier
    e2e_timeout = int(max(provider_min_ms, min(e2e_raw, e2e_max_ms)))

    return TimeoutSuggestion(
        provider_timeout_ms=provider_timeout,
        e2e_timeout_ms=e2e_timeout,
        percentile_used=percentile,
        percentile_value_ms=p_val,
        sample_count=len(values),
        warnings=warnings,
    )


def _read_csv(path: Path) -> List[float]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    # If header row contains latency_ms, skip it
    if rows and rows[0] and rows[0][0].lower().strip() == "latency_ms":
        rows = rows[1:]
    values: List[float] = []
    for row in rows:
        if not row:
            continue
        try:
            values.append(float(row[0]))
        except ValueError:
            continue
    return values


def _read_json(path: Path) -> List[float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        values: List[float] = []
        for item in data:
            if isinstance(item, (int, float)):
                values.append(float(item))
            elif isinstance(item, dict) and "latency_ms" in item:
                try:
                    values.append(float(item["latency_ms"]))
                except (TypeError, ValueError):
                    continue
        return values
    raise ValueError("JSON input must be an array")


def format_policy_snippet(suggestion: TimeoutSuggestion) -> str:
    lines = [
        "# Suggested timeouts derived from sample latency data",
        f"# samples={suggestion.sample_count} p{int(suggestion.percentile_used*100)}={suggestion.percentile_value_ms:.1f}ms warnings={','.join(suggestion.warnings) if suggestion.warnings else 'none'}",
        "timeouts:",
        f"  provider_timeout_ms: {suggestion.provider_timeout_ms}",
        f"  e2e_timeout_ms: {suggestion.e2e_timeout_ms}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline timeout suggestion helper.")
    parser.add_argument("--input", required=True, help="Path to CSV or JSON file of latencies")
    parser.add_argument("--format", choices=["csv", "json"], help="Input format (auto by extension if omitted)")
    parser.add_argument("--percentile", type=float, default=0.95, help="Percentile to base suggestion on (0-1]")
    args = parser.parse_args()

    path = Path(args.input)
    fmt = args.format
    if fmt is None:
        fmt = "json" if path.suffix.lower() == ".json" else "csv"

    if fmt == "csv":
        latencies = _read_csv(path)
    else:
        latencies = _read_json(path)

    suggestion = suggest_timeouts(latencies, percentile=args.percentile)
    print(format_policy_snippet(suggestion))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
