from skyfield.api import Topos, load, EarthSatellite
from skyfield.timelib import Time
from datetime import datetime, timezone, timedelta
from tools.tle_fetcher import fetch_tle

# Dhruva Space HQ is in Hyderabad
GROUND_STATION = {
    "name": "Dhruva Space HQ, Hyderabad",
    "lat": 17.3850,
    "lon": 78.4867,
    "elevation_m": 542
}

# Minimum elevation angle to consider a pass valid (degrees)
# Below 10° = too close to horizon, weak signal
MIN_ELEVATION_DEG = 10.0


def compute_passes(satellite_name: str, hours_ahead: int = 24) -> dict:
    """
    Compute all passes of a satellite over Hyderabad
    in the next `hours_ahead` hours.
    """

    # Step 1: Fetch TLE
    tle_data = fetch_tle(satellite_name)
    if "error" in tle_data:
        return {"error": tle_data["error"]}

    # Step 2: Build Skyfield satellite object
    satellite = EarthSatellite(
        tle_data["line1"],
        tle_data["line2"],
        tle_data["satellite"]
    )

    # Step 3: Define ground station
    ts = load.timescale()
    ground = Topos(
        latitude_degrees=GROUND_STATION["lat"],
        longitude_degrees=GROUND_STATION["lon"],
        elevation_m=GROUND_STATION["elevation_m"]
    )

    # Step 4: Define time window
    now = datetime.now(timezone.utc)
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(hours=hours_ahead))

    # Step 5: Find pass events
    # Events: 0 = AOS (Acquisition of Signal), 1 = Max elevation, 2 = LOS (Loss of Signal)
    try:
        times, events = satellite.find_events(
            ground, t0, t1,
            altitude_degrees=MIN_ELEVATION_DEG
        )
    except Exception as e:
        return {"error": f"Pass computation failed: {str(e)}"}

    # Step 6: Group events into passes
    passes = []
    current_pass = {}

    for time, event in zip(times, events):
        dt = time.utc_datetime()
        ist_offset = timedelta(hours=5, minutes=30)
        ist_time = dt + ist_offset  # Convert UTC to IST

        if event == 0:  # AOS — pass starts
            current_pass = {
                "aos_utc": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "aos_ist": ist_time.strftime("%Y-%m-%d %H:%M:%S IST"),
            }
        elif event == 1:  # Max elevation
            # Compute exact elevation at this moment
            difference = satellite - ground
            topocentric = difference.at(time)
            alt, az, distance = topocentric.altaz()
            current_pass["max_elevation_deg"] = round(alt.degrees, 2)
            current_pass["max_elevation_time_ist"] = ist_time.strftime("%H:%M:%S IST")
            current_pass["azimuth_deg"] = round(az.degrees, 2)
            current_pass["distance_km"] = round(distance.km, 1)

        elif event == 2:  # LOS — pass ends
            current_pass["los_utc"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            current_pass["los_ist"] = ist_time.strftime("%Y-%m-%d %H:%M:%S IST")

            # Compute pass duration
            if "aos_utc" in current_pass and "los_utc" in current_pass:
                aos_dt = datetime.strptime(current_pass["aos_utc"], "%Y-%m-%d %H:%M:%S UTC")
                los_dt = datetime.strptime(current_pass["los_utc"], "%Y-%m-%d %H:%M:%S UTC")
                duration_sec = int((los_dt - aos_dt).total_seconds())
                current_pass["duration_seconds"] = duration_sec
                current_pass["duration_min"] = round(duration_sec / 60, 1)

            # Quality rating based on max elevation
            elev = current_pass.get("max_elevation_deg", 0)
            if elev >= 60:
                current_pass["quality"] = "EXCELLENT"
            elif elev >= 30:
                current_pass["quality"] = "GOOD"
            else:
                current_pass["quality"] = "MARGINAL"

            passes.append(current_pass)
            current_pass = {}

    return {
        "satellite": tle_data["satellite"],
        "ground_station": GROUND_STATION["name"],
        "computed_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "window_hours": hours_ahead,
        "total_passes": len(passes),
        "passes": passes
    }


def get_next_pass(satellite_name: str) -> dict:
    """Get only the next single pass — used by the agent."""
    result = compute_passes(satellite_name, hours_ahead=24)
    if "error" in result:
        return result
    if not result["passes"]:
        return {"error": f"No passes found for {satellite_name} in next 24 hours"}

    next_pass = result["passes"][0]
    next_pass["satellite"] = result["satellite"]
    next_pass["ground_station"] = result["ground_station"]
    return next_pass


if __name__ == "__main__":
    print("=== Pass Calculator Test ===\n")
    print("📡 Computing next ISS pass over Hyderabad...\n")

    result = get_next_pass("ISS")

    if "error" not in result:
        print(f"🛰️  Satellite     : {result['satellite']}")
        print(f"📍  Ground Station: {result['ground_station']}")
        print(f"🟢  AOS (Start)   : {result['aos_ist']}")
        print(f"📈  Max Elevation : {result['max_elevation_deg']}°  at {result['max_elevation_time_ist']}")
        print(f"🔴  LOS (End)     : {result['los_ist']}")
        print(f"⏱️  Duration      : {result['duration_min']} minutes")
        print(f"⭐  Quality       : {result['quality']}")
        print(f"📏  Distance      : {result['distance_km']} km")
    else:
        print(f"❌ Error: {result['error']}")