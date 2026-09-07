
from __future__ import annotations

import json
import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable


class SensorStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    ALARM = "ALARM"


@dataclass
class SensorReading:
    """One telemetry record. This exact shape is what will later flow through
    Kafka -> GCS bronze -> Snowflake RAW. Keeping it flat and simple now makes
    every downstream layer easier to reason about."""

    reading_id: str
    device_id: str
    site_id: str
    sensor_type: str
    timestamp: str  # ISO-8601 UTC, e.g. 2026-09-07T12:30:00Z
    value: float
    unit: str
    battery_voltage: float
    status: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class BaseSensor:
    """Shared behavior for all sensor simulators: stateful baseline + drift
    + noise + occasional alarm spike. Subclasses just set the physical
    parameters (units, thresholds, drift rate)."""

    sensor_type: str = "base"
    unit: str = ""

    def __init__(
        self,
        device_id: str,
        site_id: str,
        baseline: float,
        noise_std: float,
        drift_per_tick: float,
        warning_threshold: float,
        alarm_threshold: float,
        alarm_probability: float = 0.01,
        rng: random.Random | None = None,
    ) -> None:
        self.device_id = device_id
        self.site_id = site_id
        self.value = baseline
        self.noise_std = noise_std
        self.drift_per_tick = drift_per_tick
        self.warning_threshold = warning_threshold
        self.alarm_threshold = alarm_threshold
        self.alarm_probability = alarm_probability
        self.battery_voltage = 3.9  # fresh battery, will slowly drain
        self._rng = rng or random.Random()

    def _next_value(self) -> float:
        # slow baseline drift (e.g. seasonal groundwater rise, gradual tilt)
        self.value += self._rng.uniform(-self.drift_per_tick, self.drift_per_tick)
        # measurement noise on top of the drifted baseline
        reading = self.value + self._rng.gauss(0, self.noise_std)
        # rare deliberate spike -> gives us real "alarm" events to detect later
        if self._rng.random() < self.alarm_probability:
            reading += self.alarm_threshold * self._rng.uniform(0.5, 1.5)
        return round(reading, 3)

    def _status_for(self, value: float) -> SensorStatus:
        if value >= self.alarm_threshold:
            return SensorStatus.ALARM
        if value >= self.warning_threshold:
            return SensorStatus.WARNING
        return SensorStatus.OK

    def _drain_battery(self) -> None:
        self.battery_voltage = max(3.0, self.battery_voltage - self._rng.uniform(0, 0.0005))

    def read(self) -> SensorReading:
        value = self._next_value()
        self._drain_battery()
        return SensorReading(
            reading_id=str(uuid.uuid4()),
            device_id=self.device_id,
            site_id=self.site_id,
            sensor_type=self.sensor_type,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            value=value,
            unit=self.unit,
            battery_voltage=round(self.battery_voltage, 3),
            status=self._status_for(value).value,
        )


class Piezometer(BaseSensor):
    """Measures pore water pressure in soil/rock -- critical for dam/embankment
    safety. Rising pore pressure can indicate seepage or instability risk."""

    sensor_type = "piezometer"
    unit = "kPa"

    def __init__(self, device_id: str, site_id: str, rng: random.Random | None = None):
        super().__init__(
            device_id=device_id,
            site_id=site_id,
            baseline=150.0,       # typical resting pore pressure
            noise_std=1.5,
            drift_per_tick=0.4,
            warning_threshold=180.0,
            alarm_threshold=200.0,
            alarm_probability=0.01,
            rng=rng,
        )


class StrainGauge(BaseSensor):
    """Measures deformation/strain in concrete or steel -- used on bridges and
    structural elements to assess load distribution and fatigue."""

    sensor_type = "strain_gauge"
    unit = "microstrain"

    def __init__(self, device_id: str, site_id: str, rng: random.Random | None = None):
        super().__init__(
            device_id=device_id,
            site_id=site_id,
            baseline=50.0,
            noise_std=3.0,
            drift_per_tick=0.8,
            warning_threshold=120.0,
            alarm_threshold=150.0,
            alarm_probability=0.008,
            rng=rng,
        )


class Tiltmeter(BaseSensor):
    """Measures angular displacement -- used on slopes, retaining walls, and
    embankments to detect early signs of movement/instability."""

    sensor_type = "tiltmeter"
    unit = "degrees"

    def __init__(self, device_id: str, site_id: str, rng: random.Random | None = None):
        super().__init__(
            device_id=device_id,
            site_id=site_id,
            baseline=0.5,
            noise_std=0.02,
            drift_per_tick=0.01,
            warning_threshold=1.5,
            alarm_threshold=2.0,
            alarm_probability=0.005,
            rng=rng,
        )


class CrackMeter(BaseSensor):
    """Measures displacement/opening of an existing crack -- used in tunnels
    and structures to track whether a known crack is widening over time."""

    sensor_type = "crack_meter"
    unit = "mm"

    def __init__(self, device_id: str, site_id: str, rng: random.Random | None = None):
        super().__init__(
            device_id=device_id,
            site_id=site_id,
            baseline=2.0,
            noise_std=0.05,
            drift_per_tick=0.02,
            warning_threshold=5.0,
            alarm_threshold=8.0,
            alarm_probability=0.006,
            rng=rng,
        )


SENSOR_CLASSES: dict[str, type[BaseSensor]] = {
    "piezometer": Piezometer,
    "strain_gauge": StrainGauge,
    "tiltmeter": Tiltmeter,
    "crack_meter": CrackMeter,
}


@dataclass
class MonitoringSite:
    """A collection of sensors at one physical site (e.g. one dam), so we can
    later simulate multiple sites each with their own device fleet."""

    site_id: str
    sensors: list[BaseSensor] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        site_id: str,
        sensors_per_type: int = 5,
        rng: random.Random | None = None,
    ) -> "MonitoringSite":
        rng = rng or random.Random()
        sensors: list[BaseSensor] = []
        for sensor_type, sensor_cls in SENSOR_CLASSES.items():
            for i in range(sensors_per_type):
                device_id = f"{sensor_type.upper()[:2]}-{site_id}-{i:03d}"
                sensors.append(sensor_cls(device_id=device_id, site_id=site_id, rng=rng))
        return cls(site_id=site_id, sensors=sensors)

    def read_all(self) -> Iterable[SensorReading]:
        for sensor in self.sensors:
            yield sensor.read()


def generate_batch_to_file(
    site: MonitoringSite,
    output_path: Path,
    num_ticks: int,
) -> int:
    """Generate `num_ticks` rounds of readings from every sensor at the site,
    appending one JSON object per line (JSON Lines format) to output_path.

    JSON Lines (not a single JSON array) is used deliberately -- it's the
    standard format for streaming/log-style data because you can append to
    it forever without re-parsing/rewriting the whole file, and it's exactly
    the shape Kafka consumers typically batch-write to object storage.
    """
    count = 0
    with output_path.open("a", encoding="utf-8") as f:
        for _ in range(num_ticks):
            for reading in site.read_all():
                f.write(reading.to_json() + "\n")
                count += 1
    return count
