from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from orchestrator import run_full_mission
from agents.pass_scheduler import recommend_best_pass
from agents.anomaly_detector import analyze_telemetry
from agents.eo_task_planner import plan_eo_task
from tools.telemetry_simulator import (
    generate_normal_reading,
    generate_faulty_reading,
    FAULT_SCENARIOS
)
from tools.tle_fetcher import get_available_satellites

load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this API


# ── Health check ───────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "system": "SatOps AI Agent",
        "version": "1.0.0",
        "status": "online",
        "agents": ["pass_scheduler", "anomaly_detector", "eo_task_planner"],
        "satellites": get_available_satellites()
    })


# ── Agent 1: Pass Scheduler ────────────────────────────────────
@app.route("/api/passes", methods=["GET"])
def get_passes():
    """
    GET /api/passes?satellite=CARTOSAT-3&hours=24
    Returns AI-recommended pass windows for a satellite
    """
    satellite = request.args.get("satellite", "CARTOSAT-3")
    hours = int(request.args.get("hours", 24))

    result = recommend_best_pass(satellite, hours_ahead=hours)
    return jsonify(result)


# ── Agent 2: Anomaly Detector ──────────────────────────────────
@app.route("/api/anomaly", methods=["GET"])
def get_anomaly():
    """
    GET /api/anomaly?satellite=CARTOSAT-3&fault=battery_fault
    Returns AI anomaly analysis for a satellite
    fault param is optional — omit for normal telemetry
    """
    satellite = request.args.get("satellite", "CARTOSAT-3")
    fault = request.args.get("fault", None)

    if fault and fault in FAULT_SCENARIOS:
        reading = generate_faulty_reading(fault)
    else:
        reading = generate_normal_reading()

    result = analyze_telemetry(reading, satellite_name=satellite)
    return jsonify(result)


# ── Agent 3: EO Task Planner ───────────────────────────────────
@app.route("/api/eo-plan", methods=["POST"])
def get_eo_plan():
    """
    POST /api/eo-plan
    Body: {
        "satellite": "SENTINEL-2A",
        "region": "Assam, India",
        "objective": "flood monitoring",
        "area_sq_km": 5000
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    satellite = data.get("satellite", "CARTOSAT-3")
    region = data.get("region")
    objective = data.get("objective")
    area = data.get("area_sq_km", None)

    if not region or not objective:
        return jsonify({"error": "region and objective are required"}), 400

    result = plan_eo_task(
        satellite_name=satellite,
        region=region,
        objective=objective,
        area_sq_km=area
    )
    return jsonify(result)


# ── Full Mission Orchestrator ──────────────────────────────────
@app.route("/api/mission", methods=["POST"])
def run_mission():
    """
    POST /api/mission
    Body: {
        "satellite": "CARTOSAT-3",
        "region": "Punjab, India",
        "objective": "crop health monitoring",
        "fault": null
    }
    Runs all 3 agents and returns unified mission report
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    satellite = data.get("satellite", "CARTOSAT-3")
    region = data.get("region", None)
    objective = data.get("objective", None)
    fault = data.get("fault", None)

    result = run_full_mission(
        satellite_name=satellite,
        region=region,
        eo_objective=objective,
        fault_type=fault
    )
    return jsonify(result)


# ── Utilities ──────────────────────────────────────────────────
@app.route("/api/satellites", methods=["GET"])
def get_satellites():
    """GET /api/satellites — returns list of available satellites"""
    return jsonify({
        "satellites": get_available_satellites()
    })


@app.route("/api/faults", methods=["GET"])
def get_faults():
    """GET /api/faults — returns list of injectable fault types"""
    return jsonify({
        "faults": list(FAULT_SCENARIOS.keys())
    })


if __name__ == "__main__":
    print("\n🛰️  SatOps AI Agent — Flask API")
    print("================================")
    print("Endpoints:")
    print("  GET  /                          — Health check")
    print("  GET  /api/satellites            — List satellites")
    print("  GET  /api/passes?satellite=X    — Pass schedule")
    print("  GET  /api/anomaly?satellite=X   — Anomaly analysis")
    print("  POST /api/eo-plan               — EO task plan")
    print("  POST /api/mission               — Full mission report")
    print("================================\n")
    app.run(debug=True, port=5000)