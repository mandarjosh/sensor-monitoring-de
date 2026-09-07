"""
Generate dummy data for "Vendor B" -- the deliberately messy second sensor
source (see vendor_b_sensors.py for the full rationale).

Usage:
    python producer/generate_local_vendor_b.py --site DAM01 --ticks 10
"""

from __future__ import annotations

import argparse
from pathlib import Path

from vendor_b_sensors import generate_vendor_b_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate messy Vendor B sensor readings locally.")
    parser.add_argument("--site", default="DAM01")
    parser.add_argument("--sensors-per-type", type=int, default=3)
    parser.add_argument("--ticks", type=int, default=5)
    default_out = Path(__file__).resolve().parent / "output" / "readings_vendor_b.jsonl"
    parser.add_argument("--out", default=str(default_out))
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    out_path = Path(args.out)
    stats = generate_vendor_b_batch(
        site_id=args.site,
        sensors_per_type=args.sensors_per_type,
        num_ticks=args.ticks,
        output_path=out_path,
        seed=args.seed,
    )

    print(f"Site: {args.site} (Vendor B format)")
    print(f"Output file: {out_path.resolve()}")
    print(f"Total lines written: {stats['total_lines_written']}")
    print(f"  - duplicate records injected: {stats['duplicates_injected']}")
    print(f"  - corrupted/truncated lines injected: {stats['corrupted_lines']}")
    print(f"  - readings missing battery field: {stats['missing_battery']}")


if __name__ == "__main__":
    main()
