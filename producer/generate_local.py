"""
Step 1 of the pipeline: generate dummy sensor data locally as JSON Lines.

No Kafka, no cloud -- just proving out the data model and letting us eyeball
the output shape before anything else gets built on top of it.

Usage:
    python producer/generate_local.py --site DAM01 --ticks 5 --sensors-per-type 3
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from sensors import MonitoringSite, generate_batch_to_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dummy sensor readings locally.")
    parser.add_argument("--site", default="DAM01", help="Site ID to simulate (default: DAM01)")
    parser.add_argument(
        "--sensors-per-type",
        type=int,
        default=3,
        help="How many sensors of EACH type to create at the site (default: 3)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="How many rounds of readings to generate, one round = every sensor reads once (default: 5)",
    )
    default_out = Path(__file__).resolve().parent / "output" / "readings.jsonl"
    parser.add_argument(
        "--out",
        default=str(default_out),
        help=f"Output file path (JSON Lines, appended to). Default: {default_out}",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible runs")
    args = parser.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    site = MonitoringSite.build(
        site_id=args.site,
        sensors_per_type=args.sensors_per_type,
        rng=rng,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = generate_batch_to_file(site=site, output_path=out_path, num_ticks=args.ticks)

    print(f"Site: {site.site_id}")
    print(f"Devices simulated: {len(site.sensors)} ({args.sensors_per_type} per sensor type x {len(set(s.sensor_type for s in site.sensors))} types)")
    print(f"Ticks: {args.ticks}")
    print(f"Total readings written: {total}")
    print(f"Output file: {out_path.resolve()}")


if __name__ == "__main__":
    main()
