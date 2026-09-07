"""
"Vendor B" sensor simulator -- deliberately DIFFERENT and MESSIER than
`sensors.py` (Vendor A), to simulate a realistic multi-source ingestion
problem: two IoT vendors reporting the same physical measurements in
incompatible formats.

This is one of the most common real data-engineering situations: you rarely
get to design your sources' schemas. You get what the vendor gives you, and
your bronze/silver layers have to reconcile it. If everything already arrived
clean and uniform, there would be nothing for staging models or data-quality
tests to actually do.

Differences from Vendor A, on purpose:
  - NESTED JSON instead of flat (meta / reading sub-objects)
  - Different field names entirely (`dev` not `device_id`, `v` not `value`, ...)
  - Different device-type abbreviations (PZ/SG/TM/CM instead of PI/ST/TI/CR)
  - Timestamp as Unix epoch, and INCONSISTENTLY seconds vs. milliseconds
    (a genuinely common real bug: two producers on the same team disagree
    about epoch units, and nothing crashes until someone parses it wrong)
  - Status as a numeric code (0/1/2) instead of a string enum
  - Battery reported in millivolts, not volts (unit mismatch, not just a
    naming difference -- requires a real conversion, not just a rename)
  - Data-quality problems injected on purpose:
      * some readings missing the battery field entirely (optional/absent)
      * occasional exact duplicate record (simulates at-least-once delivery /
        retry behavior, which is normal and expected in real streaming systems)
      * occasional corrupt/truncated JSON line (simulates a partial write or
        a producer crash mid-message) -- these must NOT crash whatever reads
        this file; they should be skipped/quarantined, which is itself a
        design decision our bronze-loading step will need to make later.
"""

from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path
from typing import Iterable


# Vendor B's own device-type abbreviations -- deliberately different from
# Vendor A's (PI/ST/TI/CR) to simulate two vendors never having coordinated.
VENDOR_B_TYPE_CODES = {
    "piezometer": "PZ",
    "strain_gauge": "SG",
    "tiltmeter": "TM",
    "crack_meter": "CM",
}

# Same physical baselines as Vendor A (it's the same real-world phenomena
# being measured) -- but Vendor B doesn't know or care about Vendor A's
# internal representation.
BASELINES = {
    "piezometer": dict(baseline=150.0, noise=1.5, drift=0.4, warn=180.0, alarm=200.0),
    "strain_gauge": dict(baseline=50.0, noise=3.0, drift=0.8, warn=120.0, alarm=150.0),
    "tiltmeter": dict(baseline=0.5, noise=0.02, drift=0.01, warn=1.5, alarm=2.0),
    "crack_meter": dict(baseline=2.0, noise=0.05, drift=0.02, warn=5.0, alarm=8.0),
}

STATUS_CODE = {"OK": 0, "WARNING": 1, "ALARM": 2}


class VendorBDevice:
    """Stateful simulator for one Vendor B device -- same drift/noise concept
    as Vendor A's BaseSensor, but emits Vendor B's own message shape."""

    def __init__(self, sensor_type: str, device_id: str, rng: random.Random):
        self.sensor_type = sensor_type
        self.device_id = device_id
        self._rng = rng
        params = BASELINES[sensor_type]
        self.value = params["baseline"]
        self.noise = params["noise"]
        self.drift = params["drift"]
        self.warn = params["warn"]
        self.alarm = params["alarm"]
        self.battery_mv = 3900  # millivolts, Vendor B's unit of choice

    def _status_code(self, value: float) -> int:
        if value >= self.alarm:
            return STATUS_CODE["ALARM"]
        if value >= self.warn:
            return STATUS_CODE["WARNING"]
        return STATUS_CODE["OK"]

    def read(self, rng: random.Random) -> dict:
        self.value += rng.uniform(-self.drift, self.drift)
        reading_value = round(self.value + rng.gauss(0, self.noise), 3)
        if rng.random() < 0.01:
            reading_value += self.alarm * rng.uniform(0.5, 1.5)
            reading_value = round(reading_value, 3)

        self.battery_mv = max(3000, self.battery_mv - rng.uniform(0, 0.5))

        # Inconsistent epoch units -- ~15% of readings report milliseconds
        # instead of seconds. This is realistic: it usually happens because
        # one firmware version used a different timestamp library than
        # another, and nobody standardized it.
        now = time.time()
        if rng.random() < 0.15:
            ts = int(now * 1000)  # milliseconds
        else:
            ts = int(now)  # seconds

        record = {
            "meta": {
                "dev": self.device_id,
                "loc": self.device_id.split("-")[1] if "-" in self.device_id else "UNKNOWN",
                "type": VENDOR_B_TYPE_CODES[self.sensor_type],
            },
            "reading": {
                "v": reading_value,
                "ts": ts,
            },
            "code": self._status_code(reading_value),
            "msg_id": str(uuid.uuid4()),
        }

        # ~5% of readings simply omit the battery field, as if that firmware
        # revision doesn't report it -- consumers must handle its absence.
        if rng.random() >= 0.05:
            record["batt_mv"] = round(self.battery_mv, 1)

        return record


def _maybe_corrupt(line: str, rng: random.Random) -> str:
    """With small probability, mangle an otherwise-valid JSON line to
    simulate a truncated write or transmission error. This is what a
    resilient bronze-ingestion step must be able to survive without
    crashing the whole batch."""
    if rng.random() < 0.02:
        # truncate the line at a random point -> invalid JSON
        cut = rng.randint(5, max(6, len(line) - 5))
        return line[:cut]
    return line


def generate_vendor_b_batch(
    site_id: str,
    sensors_per_type: int,
    num_ticks: int,
    output_path: Path,
    seed: int | None = None,
) -> dict:
    """Generate messy Vendor B readings to a JSON Lines file. Returns a small
    summary dict so callers can report what kind of messiness was injected
    (useful for the CLI output and for the project journal)."""
    rng = random.Random(seed)

    devices: list[VendorBDevice] = []
    for sensor_type, code in VENDOR_B_TYPE_CODES.items():
        for i in range(sensors_per_type):
            device_id = f"{code}-{site_id}-{i:03d}"
            devices.append(VendorBDevice(sensor_type=sensor_type, device_id=device_id, rng=rng))

    stats = {"total_lines_written": 0, "duplicates_injected": 0, "corrupted_lines": 0, "missing_battery": 0}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        for _ in range(num_ticks):
            for device in devices:
                record = device.read(rng)
                if "batt_mv" not in record:
                    stats["missing_battery"] += 1

                line = json.dumps(record)
                corrupted = _maybe_corrupt(line, rng)
                if corrupted != line:
                    stats["corrupted_lines"] += 1
                f.write(corrupted + "\n")
                stats["total_lines_written"] += 1

                # ~1.5% chance of emitting an exact duplicate right after --
                # simulates at-least-once delivery / retry behavior that any
                # real consumer of a message queue has to be able to handle.
                if rng.random() < 0.015:
                    f.write(line + "\n")
                    stats["duplicates_injected"] += 1
                    stats["total_lines_written"] += 1

    return stats
