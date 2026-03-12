import random
import math
from datetime import datetime, timezone

# Normal operating ranges for each sensor
NORMAL_RANGES = {
    "battery_voltage":    {"min": 26.0,  "max": 30.0,  "unit": "V"},
    "solar_panel_output": {"min": 80.0,  "max": 100.0, "unit": "W"},
    "temperature_obc":    {"min": -10.0, "max": 40.0,  "unit": "°C"},
    "temperature_battery":{"min": 0.0,   "max": 35.0,  "unit": "°C"},
    "attitude_error":     {"min": 0.0,   "max": 0.5,   "unit": "deg"},
    "signal_strength":    {"min": -90.0, "max": -60.0, "unit": "dBm"},
    "memory_usage":       {"min": 20.0,  "max": 70.0,  "unit": "%"},
    "cpu_usage":          {"min": 10.0,  "max": 60.0,  "unit": "%"},
}

# Fault scenarios we can inject for testing the anomaly detector
FAULT_SCENARIOS = {
    "battery_fault": {
        "description": "Solar panel orientation fault causing battery drain",
        "affected": {"battery_voltage": 18.0, "solar_panel_output": 20.0}
    },
    "overheating": {
        "description": "OBC overheating due to high CPU load",
        "affected": {"temperature_obc": 65.0, "cpu_usage": 95.0}
    },
    "attitude_fault": {
        "description": "Attitude control system malfunction",
        "affected": {"attitude_error": 4.5, "signal_strength": -110.0}
    },
    "memory_leak": {
        "description": "Memory leak in onboard software",
        "affected": {"memory_usage": 94.0, "cpu_usage": 88.0}
    },
}


def generate_normal_reading() -> dict:
    """Generate a single normal telemetry reading."""
    reading = {}
    for sensor, bounds in NORMAL_RANGES.items():
        # Add slight noise to make it realistic
        value = random.uniform(bounds["min"], bounds["max"])
        reading[sensor] = round(value, 2)
    return reading


def generate_faulty_reading(fault_type: str) -> dict:
    """Generate a telemetry reading with a specific fault injected."""
    if fault_type not in FAULT_SCENARIOS:
        return {"error": f"Unknown fault: {fault_type}. Available: {list(FAULT_SCENARIOS.keys())}"}

    # Start with normal reading
    reading = generate_normal_reading()

    # Inject the fault values
    fault = FAULT_SCENARIOS[fault_type]
    for sensor, bad_value in fault["affected"].items():
        # Add noise around the bad value
        noise = random.uniform(-1.0, 1.0)
        reading[sensor] = round(bad_value + noise, 2)

    reading["injected_fault"] = fault_type
    reading["fault_description"] = fault["description"]
    return reading


def generate_telemetry_stream(n: int = 5, fault_type: str = None) -> list:
    """
    Generate a stream of n telemetry readings.
    If fault_type is given, last reading will have the fault injected.
    """
    readings = []
    for i in range(n):
        ts = datetime.now(timezone.utc).isoformat()
        if fault_type and i == n - 1:
            reading = generate_faulty_reading(fault_type)
        else:
            reading = generate_normal_reading()
        reading["timestamp"] = ts
        reading["reading_id"] = i + 1
        readings.append(reading)
    return readings


def check_thresholds(reading: dict) -> list:
    """
    Rule-based pre-filter — checks if any value is outside normal range.
    Returns list of flagged sensors with their values.
    This runs BEFORE the LLM to avoid wasting API calls on normal data.
    """
    flags = []
    for sensor, bounds in NORMAL_RANGES.items():
        if sensor not in reading:
            continue
        value = reading[sensor]
        if value < bounds["min"] or value > bounds["max"]:
            flags.append({
                "sensor": sensor,
                "value": value,
                "unit": bounds["unit"],
                "normal_min": bounds["min"],
                "normal_max": bounds["max"],
                "deviation": round(value - (bounds["min"] + bounds["max"]) / 2, 2)
            })
    return flags


if __name__ == "__main__":
    print("=== Telemetry Simulator Test ===\n")

    print("1️⃣  Normal reading:")
    normal = generate_normal_reading()
    for k, v in normal.items():
        unit = NORMAL_RANGES[k]["unit"]
        print(f"   {k:<25}: {v} {unit}")

    print("\n2️⃣  Faulty reading (battery_fault):")
    faulty = generate_faulty_reading("battery_fault")
    for k, v in faulty.items():
        if k in NORMAL_RANGES:
            unit = NORMAL_RANGES[k]["unit"]
            print(f"   {k:<25}: {v} {unit}")

    print("\n3️⃣  Threshold check on faulty reading:")
    flags = check_thresholds(faulty)
    if flags:
        for f in flags:
            print(f"   ⚠️  {f['sensor']}: {f['value']} {f['unit']} (normal: {f['normal_min']}–{f['normal_max']})")
    else:
        print("   ✅ All values normal")