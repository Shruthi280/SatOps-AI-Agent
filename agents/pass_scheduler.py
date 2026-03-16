from skyfield.api import load, wgs84, EarthSatellite
from datetime import datetime, timezone, timedelta
from tools.tle_fetcher import fetch_tle
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import json

load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))

# Dhruva Space HQ — Hyderabad
GROUND_STATION = {
    "name": "Dhruva Space HQ, Hyderabad",
    "lat": 17.3850,
    "lon": 78.4867,
    "elevation_m": 542
}

MIN_ELEVATION_DEG = 10

def compute_passes(satellite_name: str, hours_ahead: int = 24) -> dict:
    # Step 1: Fetch TLE
    tle_data = fetch_tle(satellite_name)
    if "error" in tle_data:
        return {"error": tle_data["error"]}

    # Step 2: Build satellite object
    ts = load.timescale()
    satellite = EarthSatellite(
        tle_data["line1"],
        tle_data["line2"],
        tle_data["satellite"],
        ts
    )

    # Step 3: Define ground station
    ground_station = wgs84.latlon(
        GROUND_STATION["lat"],
        GROUND_STATION["lon"],
        elevation_m=GROUND_STATION["elevation_m"]
    )

    # Step 4: Search for passes in next N hours
    now = datetime.now(timezone.utc)
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(hours=hours_ahead))

    times, events = satellite.find_events(
        ground_station, t0, t1,
        altitude_degrees=MIN_ELEVATION_DEG
    )

    if len(times) == 0:
        return {
            "satellite": satellite_name,
            "ground_station": GROUND_STATION["name"],
            "passes": [],
            "message": f"No passes above {MIN_ELEVATION_DEG}° in next {hours_ahead} hours"
        }

    # Step 5: Group into passes (AOS → Max → LOS)
    passes = []
    current_pass = {}
    aos_utc = None  # store raw UTC for duration calculation

    for t, event in zip(times, events):
        dt = t.utc_datetime()  # always UTC from skyfield
        diff = satellite - ground_station
        topocentric = diff.at(t)
        alt, az, distance = topocentric.altaz()

        if event == 0:  # AOS
            aos_utc = dt  # save raw UTC for duration math
            current_pass = {
                "aos": dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
                "aos_azimuth": round(az.degrees, 1)
            }

        elif event == 1:  # Max elevation
            current_pass["max_elevation"] = round(alt.degrees, 1)
            current_pass["max_el_time"] = dt.astimezone(IST).strftime("%H:%M:%S IST")

        elif event == 2:  # LOS
            current_pass["los"] = dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            current_pass["los_azimuth"] = round(az.degrees, 1)

            # Duration using raw UTC datetimes — no timezone confusion
            duration = int((dt - aos_utc).total_seconds())
            current_pass["duration_seconds"] = duration
            current_pass["duration_minutes"] = round(duration / 60, 1)

            # Quality rating
            max_el = current_pass.get("max_elevation", 0)
            if max_el >= 60:
                current_pass["quality"] = "EXCELLENT"
            elif max_el >= 30:
                current_pass["quality"] = "GOOD"
            else:
                current_pass["quality"] = "MARGINAL"

            passes.append(current_pass)
            current_pass = {}
            aos_utc = None

    return {
        "satellite": satellite_name,
        "ground_station": GROUND_STATION["name"],
        "computed_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "hours_searched": hours_ahead,
        "total_passes": len(passes),
        "passes": passes
    }


def recommend_best_pass(satellite_name: str, hours_ahead: int = 24) -> dict:
    # Step 1: Get pass data
    pass_data = compute_passes(satellite_name, hours_ahead)

    if "error" in pass_data:
        return pass_data

    if pass_data["total_passes"] == 0:
        return {
            "satellite": satellite_name,
            "recommendation": "No passes available in the search window.",
            "passes": []
        }

    # Step 2: LLM reasoning
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are SatOps, an expert satellite ground operations AI for Dhruva Space.

Analyze these upcoming satellite passes and recommend the BEST one for scheduling
a communication/data downlink session.

Satellite: {satellite}
Ground Station: {ground_station}
Upcoming Passes:
{passes}

Respond ONLY in this exact JSON format, no extra text:
{{
    "recommended_pass": 1,
    "reasoning": "brief explanation of why this pass is best",
    "confidence": 0.92,
    "warnings": "any concerns or empty string",
    "suggested_action": "specific action for the operator"
}}
""")

    chain = prompt | llm

    response = chain.invoke({
        "satellite": pass_data["satellite"],
        "ground_station": pass_data["ground_station"],
        "passes": json.dumps(pass_data["passes"], indent=2)
    })

    # Step 3: Parse LLM response
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        llm_output = json.loads(content.strip())
    except json.JSONDecodeError:
        llm_output = {
            "recommended_pass": 1,
            "reasoning": response.content,
            "confidence": 0.5,
            "warnings": "LLM returned unstructured response",
            "suggested_action": "Manual review recommended"
        }

    # Step 4: Confidence guardrail
    confidence = llm_output.get("confidence", 0)
    if confidence < 0.75:
        llm_output["human_review_required"] = True
        llm_output["review_reason"] = "Low confidence — escalated to operator"
    else:
        llm_output["human_review_required"] = False

    return {
        "satellite": satellite_name,
        "ground_station": pass_data["ground_station"],
        "computed_at": pass_data["computed_at"],
        "total_passes": pass_data["total_passes"],
        "passes": pass_data["passes"],
        "ai_recommendation": llm_output
    }


if __name__ == "__main__":
    print("=== Pass Scheduler Agent (with AI) ===\n")
    result = recommend_best_pass("ISS", hours_ahead=12)

    print(f"Satellite     : {result['satellite']}")
    print(f"Ground Station: {result['ground_station']}")
    print(f"Total Passes  : {result['total_passes']}\n")

    print("--- All Passes ---")
    for i, p in enumerate(result["passes"], 1):
        print(f"Pass {i}: {p['aos']} | Max El: {p['max_elevation']}° | Duration: {p['duration_minutes']} mins | {p['quality']}")

    print("\n--- 🤖 AI Recommendation ---")
    rec = result["ai_recommendation"]
    print(f"Best Pass     : Pass {rec['recommended_pass']}")
    print(f"Reasoning     : {rec['reasoning']}")
    print(f"Confidence    : {rec['confidence']}")
    print(f"Warnings      : {rec['warnings']}")
    print(f"Action        : {rec['suggested_action']}")
    print(f"Human Review  : {'⚠️  YES' if rec['human_review_required'] else '✅ Not required'}")