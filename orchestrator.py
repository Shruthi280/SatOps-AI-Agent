import json
from datetime import datetime, timezone,timedelta
from dotenv import load_dotenv
from agents.pass_scheduler import recommend_best_pass
from agents.anomaly_detector import analyze_telemetry
from agents.eo_task_planner import plan_eo_task
from tools.telemetry_simulator import generate_normal_reading, generate_faulty_reading
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

IST = timezone(timedelta(hours=5, minutes=30))

load_dotenv()

def run_full_mission(
    satellite_name: str,
    region: str = None,
    eo_objective: str = None,
    fault_type: str = None
) -> dict:
    """
    Master orchestrator — runs all 3 agents for a given satellite
    and combines their outputs into one unified mission report.
    
    Args:
        satellite_name : which satellite to operate
        region         : target region for EO task (optional)
        eo_objective   : what to image and why (optional)
        fault_type     : inject a specific fault for testing (optional)
    """

    print(f"\n{'='*55}")
    print(f"  🛰️  SatOps Mission Control — {satellite_name}")
    print(f"{'='*55}")
    report = {
        "satellite": satellite_name,
        "mission_start": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "agents": {}
    }

    # ── Agent 1: Pass Scheduler ────────────────────────────────
    print("\n📡 Agent 1: Computing pass windows...")
    try:
        pass_result = recommend_best_pass(satellite_name, hours_ahead=24)
        report["agents"]["pass_scheduler"] = pass_result
        rec = pass_result.get("ai_recommendation", {})
        print(f"   Total passes   : {pass_result.get('total_passes', 0)}")
        print(f"   Best pass      : Pass {rec.get('recommended_pass', 'N/A')}")
        print(f"   Confidence     : {rec.get('confidence', 'N/A')}")
        print(f"   Human review   : {'⚠️  YES' if rec.get('human_review_required') else '✅ No'}")
    except Exception as e:
        report["agents"]["pass_scheduler"] = {"error": str(e)}
        print(f"   ❌ Error: {e}")

    # ── Agent 2: Anomaly Detector ──────────────────────────────
    print("\n🔬 Agent 2: Analyzing telemetry...")
    try:
        if fault_type:
            reading = generate_faulty_reading(fault_type)
            print(f"   ⚠️  Fault injected: {fault_type}")
        else:
            reading = generate_normal_reading()

        anomaly_result = analyze_telemetry(reading, satellite_name=satellite_name)
        report["agents"]["anomaly_detector"] = anomaly_result
        print(f"   Status         : {anomaly_result['status']}")

        if anomaly_result["status"] != "NOMINAL":
            ai = anomaly_result["ai_analysis"]
            print(f"   Component      : {ai.get('affected_component', 'N/A')}")
            print(f"   Severity       : {ai.get('severity', 'N/A')}")
            print(f"   Confidence     : {ai.get('confidence', 'N/A')}")
            print(f"   Human review   : {'⚠️  YES' if ai.get('human_review_required') else '✅ No'}")
        else:
            print(f"   ✅ All systems nominal")
    except Exception as e:
        report["agents"]["anomaly_detector"] = {"error": str(e)}
        print(f"   ❌ Error: {e}")

    # ── Agent 3: EO Task Planner ───────────────────────────────
    if region and eo_objective:
        print("\n🌍 Agent 3: Planning EO imaging task...")
        try:
            eo_result = plan_eo_task(
                satellite_name=satellite_name,
                region=region,
                objective=eo_objective
            )
            report["agents"]["eo_task_planner"] = eo_result
            plan = eo_result.get("task_plan", {})
            print(f"   Mission        : {plan.get('mission_name', 'N/A')}")
            print(f"   Bands          : {plan.get('recommended_bands', 'N/A')}")
            print(f"   Revisit        : {plan.get('revisit_frequency', 'N/A')}")
            print(f"   Confidence     : {plan.get('confidence', 'N/A')}")
            print(f"   Human review   : {'⚠️  YES' if plan.get('human_review_required') else '✅ No'}")
        except Exception as e:
            report["agents"]["eo_task_planner"] = {"error": str(e)}
            print(f"   ❌ Error: {e}")
    else:
        print("\n🌍 Agent 3: Skipped (no region/objective provided)")
        report["agents"]["eo_task_planner"] = {"status": "skipped"}

    # ── Final Summary by LLM ───────────────────────────────────
    print("\n🧠 Generating mission summary...")
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        prompt = ChatPromptTemplate.from_template("""
You are SatOps Mission Control AI for Dhruva Space.

Generate a concise mission briefing based on these agent outputs:

Satellite: {satellite}
Pass Scheduler Result: {pass_result}
Anomaly Detector Result: {anomaly_result}
EO Task Planner Result: {eo_result}

Respond ONLY in this JSON format:
{{
    "mission_status": "GO / NO-GO / CAUTION",
    "summary": "2-3 sentence plain English briefing",
    "priority_action": "single most important thing operator should do now",
    "all_systems_go": true
}}

mission_status rules:
- GO      : no anomalies, passes available, plan ready
- CAUTION : warnings present or low confidence
- NO-GO   : critical anomaly detected
""")

        chain = prompt | llm

        response = chain.invoke({
            "satellite": satellite_name,
            "pass_result": json.dumps({
                "total_passes": report["agents"]["pass_scheduler"].get("total_passes", 0),
                "recommendation": report["agents"]["pass_scheduler"].get("ai_recommendation", {})
            }, indent=2),
            "anomaly_result": json.dumps({
                "status": report["agents"]["anomaly_detector"].get("status", "UNKNOWN"),
                "ai_analysis": report["agents"]["anomaly_detector"].get("ai_analysis", {})
            }, indent=2),
            "eo_result": json.dumps({
                "task_plan": report["agents"].get("eo_task_planner", {}).get("task_plan", {})
            }, indent=2)
        })

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        summary = json.loads(content.strip())
        report["mission_summary"] = summary

        print(f"\n{'='*55}")
        print(f"  📋 MISSION BRIEFING — {satellite_name}")
        print(f"{'='*55}")
        print(f"  Status   : {summary['mission_status']}")
        print(f"  Summary  : {summary['summary']}")
        print(f"  Action   : {summary['priority_action']}")
        print(f"{'='*55}\n")

    except Exception as e:
        report["mission_summary"] = {"error": str(e)}
        print(f"   ❌ Summary error: {e}")

    report["mission_end"] = datetime.now(timezone.utc).isoformat()
    return report


if __name__ == "__main__":

    # Mission 1: Normal ops — CARTOSAT-3 crop monitoring
    run_full_mission(
        satellite_name="CARTOSAT-3",
        region="Punjab, India",
        eo_objective="crop health monitoring",
        fault_type=None
    )

    # Mission 2: Emergency — SENTINEL-2A with battery fault
    run_full_mission(
        satellite_name="SENTINEL-2A",
        region="Assam, India",
        eo_objective="flood monitoring",
        fault_type="battery_fault"
    )