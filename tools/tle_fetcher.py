import requests
from datetime import datetime, timezone

# Correct CelesTrak endpoints
CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_SUP_URL = "https://celestrak.org/NORAD/elements/supplemental/sup-gp.php"

SATELLITE_IDS = {
    "ISS":          "25544",
    "RESOURCESAT-2": "37387",  # Indian satellite
    "CARTOSAT-3":   "44233",   # Indian EO satellite
    "SENTINEL-2A":  "40697",   # EO satellite
}

def fetch_tle(satellite_name: str) -> dict:
    """
    Fetch TLE data for a satellite from CelesTrak.
    Returns dict with name, line1, line2, fetched_at.
    """
    sat_id = SATELLITE_IDS.get(satellite_name.upper())

    if not sat_id:
        return {"error": f"Satellite '{satellite_name}' not found. Available: {list(SATELLITE_IDS.keys())}"}

    url = f"{CELESTRAK_GP_URL}?CATNR={sat_id}&FORMAT=TLE"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]

        if len(lines) < 3:
            return {"error": "Invalid TLE data received from CelesTrak"}

        # Validate TLE format
        if not lines[1].startswith("1 ") or not lines[2].startswith("2 "):
            return {"error": "TLE format validation failed"}

        return {
            "satellite": lines[0],
            "line1":     lines[1],
            "line2":     lines[2],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source":    "CelesTrak"
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}


def fetch_all_satellites() -> list:
    """Fetch TLE data for all satellites in our list."""
    results = []
    for name in SATELLITE_IDS:
        print(f"Fetching TLE for {name}...")
        tle = fetch_tle(name)
        results.append(tle)
    return results


if __name__ == "__main__":
    print("=== TLE Fetcher Test ===\n")
    tle = fetch_tle("ISS")
    if "error" not in tle:
        print(f"✅ Satellite : {tle['satellite']}")
        print(f"   Line 1   : {tle['line1']}")
        print(f"   Line 2   : {tle['line2']}")
        print(f"   Fetched  : {tle['fetched_at']}")
    else:
        print(f"❌ Error: {tle['error']}")