import json
from datetime import datetime, timezone
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from tools.telemetry_simulator import (
    generate_normal_reading,
    generate_faulty_reading,
    check_thresholds
)

load_dotenv()

def analyze_telemetry(reading: dict, satellite_name: str = "CARTOSAT-3") -> dict:
    """
    Analyzes satellite telemetry for anomalies.
    Step 1: Rule-based threshold check
    Step 2: LLM classifies severity + generates report
    Step 3: Confidence guardrail → human review if needed
    """

    # ── Step 1: Rule-based pre-filter ─────────────────────────
    flags = check_thresholds(reading)

    if not flags:
        return {
            "status": "NOMINAL",
            "message": "All parameters within normal range",
            "human_review_required": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ── Step 2: LLM analysis ───────────────────────────────────
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are SatOps Anomaly Detector, an expert satellite health monitoring AI for Dhruva Space.

Satellite under monitoring: {satellite}

A rule-based system flagged these sensors as outside normal range:
{flags}

Full telemetry snapshot:
{telemetry}

Analyze the anomaly and respond ONLY in this exact JSON format, no extra text:
{{
    "severity": "WARNING",
    "affected_component": "battery system",
    "root_cause": "brief likely cause",
    "confidence": 0.91,
    "reasoning": "explanation of what the data shows",
    "suggested_action": "specific action for the operator",
    "risk_if_ignored": "what happens if this is not addressed"
}}

Severity must be exactly one of: INFO, WARNING, CRITICAL
""")

    chain = prompt | llm

    # Clean telemetry — remove metadata before sending to LLM
    clean_telemetry = {
        k: v for k, v in reading.items()
        if k not in ["timestamp", "reading_id", "injected_fault", "fault_description"]
    }

    response = chain.invoke({
    "flags": json.dumps(flags, indent=2),
    "telemetry": json.dumps(clean_telemetry, indent=2),
    "satellite": satellite_name
    })
    # ── Step 3: Parse LLM response ─────────────────────────────
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        llm_output = json.loads(content.strip())
    except json.JSONDecodeError:
        llm_output = {
            "severity": "WARNING",
            "affected_component": "unknown",
            "root_cause": "Could not parse LLM response",
            "confidence": 0.5,
            "reasoning": response.content,
            "suggested_action": "Manual inspection recommended",
            "risk_if_ignored": "Unknown"
        }

    # ── Step 4: Confidence + severity guardrails ───────────────
    confidence = llm_output.get("confidence", 0)
    severity = llm_output.get("severity", "WARNING")

    if severity == "CRITICAL" or confidence < 0.75:
        llm_output["human_review_required"] = True
        llm_output["review_reason"] = (
            "CRITICAL severity — operator approval required"
            if severity == "CRITICAL"
            else "Low confidence — escalated to operator"
        )
    else:
        llm_output["human_review_required"] = False

    # ── Step 5: Build final report ─────────────────────────────
    return {
        "status": severity,
        "flagged_sensors": flags,
        "ai_analysis": llm_output,
        "raw_telemetry": reading,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    print("=== Anomaly Detector Test ===\n")

    # Test 1: Normal telemetry
    print("--- Test 1: Normal Telemetry ---")
    normal = generate_normal_reading()
    result = analyze_telemetry(normal,satellite_name="CARTOSAT-3")
    print(f"Status  : {result['status']}")
    print(f"Message : {result.get('message', 'N/A')}\n")

    # Test 2: Battery fault
    print("--- Test 2: Battery Fault ---")
    faulty = generate_faulty_reading("battery_fault")
    result = analyze_telemetry(faulty,satellite_name="CARTOSAT-3")
    ai = result["ai_analysis"]
    print(f"Status          : {result['status']}")
    print(f"Flagged Sensors : {[f['sensor'] for f in result['flagged_sensors']]}")
    print(f"Component       : {ai['affected_component']}")
    print(f"Root Cause      : {ai['root_cause']}")
    print(f"Confidence      : {ai['confidence']}")
    print(f"Reasoning       : {ai['reasoning']}")
    print(f"Action          : {ai['suggested_action']}")
    print(f"Risk if Ignored : {ai['risk_if_ignored']}")
    print(f"Human Review    : {'⚠️  YES — ' + ai.get('review_reason','') if ai['human_review_required'] else '✅ Not required'}")

    print()

    # Test 3: Overheating
    print("--- Test 3: Overheating ---")
    hot = generate_faulty_reading("overheating")
    result = analyze_telemetry(hot,satellite_name="CARTOSAT-3")
    ai = result["ai_analysis"]
    print(f"Status          : {result['status']}")
    print(f"Flagged Sensors : {[f['sensor'] for f in result['flagged_sensors']]}")
    print(f"Component       : {ai['affected_component']}")
    print(f"Action          : {ai['suggested_action']}")
    print(f"Human Review    : {'⚠️  YES — ' + ai.get('review_reason','') if ai['human_review_required'] else '✅ Not required'}")

    print()

    # Test 4: Attitude fault
    print("--- Test 4: Attitude Fault ---")
    attitude = generate_faulty_reading("attitude_fault")
    result = analyze_telemetry(attitude,satellite_name="CARTOSAT-3")
    ai = result["ai_analysis"]
    print(f"Status          : {result['status']}")
    print(f"Flagged Sensors : {[f['sensor'] for f in result['flagged_sensors']]}")
    print(f"Component       : {ai['affected_component']}")
    print(f"Action          : {ai['suggested_action']}")
    print(f"Human Review    : {'⚠️  YES — ' + ai.get('review_reason','') if ai['human_review_required'] else '✅ Not required'}")

# Sanity check — verify AI flagged the right sensors
def verify_result(result, expected_sensors, expected_severity):
    flagged = [f['sensor'] for f in result['flagged_sensors']]
    actual_severity = result['status']
    
    sensors_correct = all(s in flagged for s in expected_sensors)
    severity_correct = actual_severity == expected_severity
    
    print(f"  Sensors correct  : {'✅' if sensors_correct else '❌'}")
    print(f"  Severity correct : {'✅' if severity_correct else '❌'}")

print("\n--- Sanity Checks ---")
faulty = generate_faulty_reading("battery_fault")
result = analyze_telemetry(faulty, satellite_name="CARTOSAT-3")
verify_result(result, ["battery_voltage", "solar_panel_output"], "CRITICAL")