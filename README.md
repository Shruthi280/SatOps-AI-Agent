🛰️ SatOps AI Agent
A multi-agent AI system for LEO satellite operations — TLE-based pass scheduling, telemetry anomaly detection with auto-generated incident reports, and Earth observation task planning.

What it does

Pass Scheduler — fetches live TLE data and recommends the best upcoming contact window
Anomaly Detector — analyzes satellite telemetry and auto-generates incident reports when faults are found
EO Task Planner — plans Earth observation missions (bands, revisit rate, resolution) for a target region
Mission Orchestrator — runs all three agents and returns a unified GO / CAUTION / NO-GO briefing

🏗️ Architecture

                    ┌─────────────────────────────────────────┐
                    │         Operators Dashboard              │
                    │    (React Frontend / Grafana UI)         │
                    └──────────────────┬──────────────────────┘
                                       │ HTTP REST
                    ┌──────────────────▼──────────────────────┐
                    │        Flask API — app.py                │
                    │   /api/passes  /api/anomaly              │
                    │   /api/eo-plan /api/mission /metrics     │
                    └──┬──────────────┬────────────┬──────────┘
                       │              │            │
           ┌───────────▼──┐  ┌────────▼───┐  ┌────▼──────────┐
           │ Pass         │  │ Anomaly    │  │ EO Task       │
           │ Scheduler    │  │ Detector   │  │ Planner       │
           └──────┬───────┘  └─────┬──────┘  └──────┬────────┘
                  │                │                  │
         ┌────────▼────────┐  ┌────▼────┐   ┌────────▼───────┐
         │ TLE Fetcher     │  │Telemetry│   │ Satellite      │
         │ (CelesTrak API) │  │Simulator│   │ Capability DB  │
         │ + Pass Calc     │  │+ Thresh.│   │+ Cloud Cover   │
         │ (Skyfield)      │  │ Checks  │   │ (Open-Meteo)   │
         └─────────────────┘  └─────────┘   └────────────────┘
                       │              │
              ┌─────────▼──────────────▼───────────┐
              │    Groq LLM — Llama-3.3-70b        │
              │  (Pass Rec | Anomaly | EO | Summary)│
              └────────────────────────────────────┘


🤖 Agents

| Agent | Endpoint | Schedule (Airflow) | LLM Used |
|---|---|---|---|
| **Pass Scheduler** | `GET /api/passes` | Every 6h | Llama-3.3-70b |
| **Anomaly Detector** | `GET /api/anomaly` | Every 5min | Llama-3.3-70b |
| **EO Task Planner** | `POST /api/eo-plan` | On-demand | Llama-3.3-70b |
| **Mission Orchestrator** | `POST /api/mission` | On-demand | Llama-3.3-70b |


Setup
bashgit clone https://github.com/Shruthi280/SatOps-AI-Agent.git
cd SatOps-AI-Agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
Create a .env file in the root:
envGROQ_API_KEY=your_groq_api_key_here

Get a free key at console.groq.com


Run
Start the API server:
bashpython app.py
Or run demo missions directly:
bashpython orchestrator.py

API Endpoints
MethodEndpointDescriptionGET/api/passes?satellite=CARTOSAT-3Pass scheduleGET/api/anomaly?satellite=CARTOSAT-3&fault=battery_faultAnomaly detectionPOST/api/eo-planEO task planPOST/api/missionFull mission reportGET/api/satellitesList available satellitesGET/api/faultsList injectable fault types
Example — full mission:
bashcurl -X POST http://localhost:5000/api/mission \
  -H "Content-Type: application/json" \
  -d '{"satellite":"CARTOSAT-3","region":"Punjab, India","objective":"crop health monitoring"}'

Project Structure
SatOps-AI-Agent/
├── app.py                  # Flask API
├── orchestrator.py         # Runs all 3 agents + LLM summary
├── agents/
│   ├── pass_scheduler.py
│   ├── anomaly_detector.py
│   └── eo_task_planner.py
└── tools/
    ├── tle_fetcher.py
    └── telemetry_simulator.py

Tech Stack
Python · LangChain · Groq (LLaMA 3.3 70B) · Skyfield · Flask · ChromaDB
