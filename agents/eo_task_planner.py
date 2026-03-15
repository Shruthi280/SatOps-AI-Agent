import json
from datetime import datetime, timezone,timedelta
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from tools.tle_fetcher import fetch_tle, get_available_satellites

load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))
# EO satellite capabilities knowledge base
# In V2 this will be replaced by RAG over actual satellite spec docs
SATELLITE_CAPABILITIES = {
    "CARTOSAT-3": {
        "type": "Optical",
        "resolution": "0.28m panchromatic, 1.12m multispectral",
        "swath_width": "16.5 km",
        "bands": ["PAN", "RGB", "NIR"],
        "best_for": ["urban mapping", "infrastructure", "defence", "disaster assessment"],
        "revisit_days": 4,
        "altitude_km": 509,
        "limitations": "Cannot image through clouds"
    },
    "RESOURCESAT-2": {
        "type": "Multispectral",
        "resolution": "5.8m LISS-4, 23.5m LISS-3, 56m AWiFS",
        "swath_width": "70 km (LISS-4), 141 km (LISS-3)",
        "bands": ["GREEN", "RED", "NIR", "SWIR"],
        "best_for": ["agriculture", "forestry", "water bodies", "land use"],
        "revisit_days": 5,
        "altitude_km": 817,
        "limitations": "Lower resolution than CARTOSAT-3"
    },
    "SENTINEL-2A": {
        "type": "Multispectral",
        "resolution": "10m (visible/NIR), 20m (red edge/SWIR), 60m (coastal/water vapor)",
        "swath_width": "290 km",
        "bands": ["BLUE", "GREEN", "RED", "NIR", "SWIR", "RED_EDGE", "COASTAL"],
        "best_for": ["vegetation monitoring", "crop health", "water quality", "flood mapping"],
        "revisit_days": 5,
        "altitude_km": 786,
        "limitations": "Cannot penetrate clouds or image at night"
    },
    "ISS": {
        "type": "Research platform",
        "resolution": "varies by instrument",
        "swath_width": "varies",
        "bands": ["RGB", "NIR"],
        "best_for": ["experimental imaging", "atmospheric research"],
        "revisit_days": 1,
        "altitude_km": 408,
        "limitations": "Not a dedicated EO satellite"
    }
}

# Common EO use cases and what they need
USE_CASE_REQUIREMENTS = {
    "flood monitoring":       {"preferred_bands": ["NIR", "SWIR"], "revisit": "daily", "notes": "SAR preferred for cloud penetration"},
    "crop health":            {"preferred_bands": ["NIR", "RED_EDGE", "SWIR"], "revisit": "weekly", "notes": "NDVI computation needed"},
    "urban mapping":          {"preferred_bands": ["PAN", "RGB"], "revisit": "monthly", "notes": "High resolution critical"},
    "disaster assessment":    {"preferred_bands": ["RGB", "NIR", "SWIR"], "revisit": "daily", "notes": "Rapid response needed"},
    "deforestation tracking": {"preferred_bands": ["NIR", "SWIR", "RED_EDGE"], "revisit": "biweekly", "notes": "Change detection algorithm needed"},
    "water quality":          {"preferred_bands": ["COASTAL", "NIR", "RED_EDGE"], "revisit": "weekly", "notes": "Turbidity and chlorophyll indices"},
    "infrastructure":         {"preferred_bands": ["PAN", "RGB"], "revisit": "monthly", "notes": "Sub-meter resolution preferred"},
    "defence surveillance":   {"preferred_bands": ["PAN", "NIR"], "revisit": "daily", "notes": "High resolution + rapid tasking"},
}


def plan_eo_task(
    satellite_name: str,
    region: str,
    objective: str,
    area_sq_km: float = None
) -> dict:
    """
    Plans an Earth Observation imaging task for a given satellite,
    region, and objective using AI reasoning.
    """

    # ── Step 1: Validate satellite ─────────────────────────────
    satellite_name = satellite_name.upper()
    if satellite_name not in SATELLITE_CAPABILITIES:
        return {
            "error": f"Satellite '{satellite_name}' not in knowledge base.",
            "available": get_available_satellites()
        }

    sat_caps = SATELLITE_CAPABILITIES[satellite_name]

    # ── Step 2: Match objective to use case ────────────────────
    matched_use_case = None
    for use_case in USE_CASE_REQUIREMENTS:
        if use_case.lower() in objective.lower():
            matched_use_case = USE_CASE_REQUIREMENTS[use_case]
            break

    # ── Step 3: LLM task planning ──────────────────────────────
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are SatOps EO Task Planner, an expert Earth Observation mission planning AI for Dhruva Space.

Plan an imaging task for the following request:

Satellite       : {satellite}
Target Region   : {region}
Mission Objective: {objective}
Area (sq km)    : {area}

Satellite Capabilities:
{capabilities}

Known Requirements for this type of mission:
{use_case_requirements}

Respond ONLY in this exact JSON format, no extra text:
{{
    "mission_name": "short descriptive name",
    "recommended_bands": ["NIR", "SWIR"],
    "imaging_schedule": "when and how often to image",
    "revisit_frequency": "e.g. every 2 days",
    "estimated_passes_needed": 3,
    "confidence": 0.91,
    "reasoning": "why these bands and schedule for this objective",
    "data_products": ["NDVI map", "change detection"],
    "preprocessing_steps": ["atmospheric correction", "cloud masking"],
    "limitations": "any satellite limitations for this task",
    "suggested_action": "immediate next step for the operator"
}}
""")

    chain = prompt | llm

    response = chain.invoke({
        "satellite": satellite_name,
        "region": region,
        "objective": objective,
        "area": area_sq_km or "not specified",
        "capabilities": json.dumps(sat_caps, indent=2),
        "use_case_requirements": json.dumps(matched_use_case, indent=2) if matched_use_case else "No exact match — use best judgment"
    })

    # ── Step 4: Parse response ─────────────────────────────────
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        llm_output = json.loads(content.strip())
    except json.JSONDecodeError:
        llm_output = {
            "mission_name": "Manual Planning Required",
            "confidence": 0.5,
            "reasoning": response.content,
            "suggested_action": "Manual review required",
            "limitations": "Could not parse AI response"
        }

    # ── Step 5: Confidence guardrail ───────────────────────────
    confidence = llm_output.get("confidence", 0)
    llm_output["human_review_required"] = confidence < 0.75

    # ── Step 6: Build final plan ───────────────────────────────
    return {
        "satellite": satellite_name,
        "region": region,
        "objective": objective,
        "satellite_capabilities": sat_caps,
        "task_plan": llm_output,
        "planned_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    }


if __name__ == "__main__":
    print("=== EO Task Planner Test ===\n")

    # Test 1: Flood monitoring
    print("--- Test 1: Flood Monitoring (Assam) ---")
    result = plan_eo_task(
        satellite_name="SENTINEL-2A",
        region="Assam, India",
        objective="flood monitoring and water extent mapping",
        area_sq_km=5000
    )
    plan = result["task_plan"]
    print(f"Mission         : {plan['mission_name']}")
    print(f"Bands           : {plan['recommended_bands']}")
    print(f"Schedule        : {plan['imaging_schedule']}")
    print(f"Revisit         : {plan['revisit_frequency']}")
    print(f"Data Products   : {plan['data_products']}")
    print(f"Confidence      : {plan['confidence']}")
    print(f"Reasoning       : {plan['reasoning']}")
    print(f"Action          : {plan['suggested_action']}")
    print(f"Human Review    : {'⚠️  YES' if plan['human_review_required'] else '✅ Not required'}")

    print()

    # Test 2: Crop health monitoring
    print("--- Test 2: Crop Health (Punjab) ---")
    result = plan_eo_task(
        satellite_name="RESOURCESAT-2",
        region="Punjab, India",
        objective="crop health monitoring and yield estimation",
        area_sq_km=15000
    )
    plan = result["task_plan"]
    print(f"Mission         : {plan['mission_name']}")
    print(f"Bands           : {plan['recommended_bands']}")
    print(f"Revisit         : {plan['revisit_frequency']}")
    print(f"Action          : {plan['suggested_action']}")
    print(f"Human Review    : {'⚠️  YES' if plan['human_review_required'] else '✅ Not required'}")

    print()

    # Test 3: Disaster assessment
    print("--- Test 3: Disaster Assessment (Chennai) ---")
    result = plan_eo_task(
        satellite_name="CARTOSAT-3",
        region="Chennai, Tamil Nadu",
        objective="disaster assessment after cyclone landfall",
        area_sq_km=1000
    )
    plan = result["task_plan"]
    print(f"Mission         : {plan['mission_name']}")
    print(f"Bands           : {plan['recommended_bands']}")
    print(f"Revisit         : {plan['revisit_frequency']}")
    print(f"Action          : {plan['suggested_action']}")
    print(f"Human Review    : {'⚠️  YES' if plan['human_review_required'] else '✅ Not required'}")