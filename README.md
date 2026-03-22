# 🛰️ SatOps AI Agent

A **multi-agent AI system for LEO satellite operations** that simulates real-world satellite mission workflows using **TLE-based pass scheduling**, **telemetry anomaly detection**, and **Earth Observation (EO) task planning**.

Built to demonstrate how **AI agents can assist satellite mission control** by combining rule-based systems, orbital mechanics, and LLM-powered reasoning into a unified operations pipeline.

---

## 🚀 Overview

**SatOps AI Agent** is designed as a lightweight mission-control simulation platform for **Low Earth Orbit (LEO) satellite operations**.

It includes **three specialized AI agents**:

- **Pass Scheduler Agent** → Computes upcoming satellite passes over a ground station using real **TLE data**
- **Anomaly Detector Agent** → Detects abnormal telemetry using rule-based thresholds + LLM analysis
- **EO Task Planner Agent** → Plans imaging missions for Earth observation satellites based on mission objectives

A **Mission Orchestrator** coordinates all agents and produces a **single mission-level GO / CAUTION / NO-GO briefing**.

---

## ✨ Features

### 1) 🛰️ Pass Scheduler Agent
- Fetches **live TLE data** from **CelesTrak**
- Uses **Skyfield** for orbital calculations
- Computes:
  - AOS (Acquisition of Signal)
  - Max elevation
  - LOS (Loss of Signal)
  - Pass duration
  - Pass quality (`EXCELLENT`, `GOOD`, `MARGINAL`)
- Uses an LLM to recommend the **best pass for communication/downlink**
- Adds a **human-review guardrail** if confidence is low

### 2) ⚠️ Telemetry Anomaly Detector Agent
- Simulates normal and faulty telemetry
- Performs **rule-based threshold checks first** (to avoid unnecessary LLM calls)
- If anomalies are detected, an LLM:
  - classifies severity (`INFO`, `WARNING`, `CRITICAL`)
  - identifies likely affected subsystem
  - suggests operator action
  - estimates risk if ignored
- Escalates for **human review** on:
  - `CRITICAL` severity
  - low confidence responses

### 3) 🌍 EO Task Planner Agent
- Plans Earth Observation imaging tasks based on:
  - target region
  - mission objective
  - area size
  - satellite capability knowledge base
- Supports example satellites such as:
  - `CARTOSAT-3`
  - `RESOURCESAT-2`
  - `SENTINEL-2A`
  - `ISS` (experimental/demo)
- Recommends:
  - spectral bands
  - revisit schedule
  - estimated passes needed
  - data products
  - preprocessing steps
  - mission limitations

### 4) 🧠 Mission Orchestrator
- Runs all agents together in sequence
- Produces a **unified mission briefing**
- Returns:
  - mission status (`GO`, `CAUTION`, `NO-GO`)
  - concise summary
  - highest priority operator action
  - overall readiness signal

### 5) 🌐 Flask REST API
Exposes the full system as easy-to-test API endpoints for frontend integration or demos.

---

## 🏗️ Architecture

```text
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
```

---

## 📁 Project Structure

```bash
SatOps-AI-Agent/
│
├── agents/
│   ├── pass_scheduler.py        # Pass computation + AI recommendation
│   ├── anomaly_detector.py      # Telemetry anomaly detection + AI analysis
│   └── eo_task_planner.py       # Earth observation mission planning
│
├── tools/
│   ├── tle_fetcher.py           # Fetches TLE data from CelesTrak
│   └── telemetry_simulator.py   # Generates normal/faulty telemetry
│
├── app.py                       # Flask REST API
├── orchestrator.py              # Runs full multi-agent mission workflow
├── requirements.txt             # Python dependencies
└── README.md
```

---

## 🛠️ Tech Stack

- **Python**
- **Flask** + **Flask-CORS**
- **Skyfield** (orbital mechanics / pass prediction)
- **LangChain**
- **Groq LLM API** (`llama-3.3-70b-versatile`)
- **Google GenAI / OpenAI support in requirements for future extensibility**
- **Requests**
- **python-dotenv**

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/Shruthi280/SatOps-AI-Agent.git
cd SatOps-AI-Agent
```

### 2. Create a virtual environment
```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows**
```bash
venv\Scripts\activate
```

**macOS / Linux**
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

> **Note:** The current implementation uses **Groq** for the main LLM reasoning pipeline.

---

## ▶️ Running the Project

### Start the Flask API
```bash
python app.py
```

The API will run on:

```bash
http://127.0.0.1:5000
```

---

## 🌐 API Endpoints

### 1. Health Check
**GET** `/`

Returns system metadata, agent list, and supported satellites.

#### Example
```bash
curl http://127.0.0.1:5000/
```

---

### 2. List Available Satellites
**GET** `/api/satellites`

#### Example
```bash
curl http://127.0.0.1:5000/api/satellites
```

---

### 3. List Injectable Fault Scenarios
**GET** `/api/faults`

#### Example
```bash
curl http://127.0.0.1:5000/api/faults
```

---

### 4. Get Pass Schedule Recommendation
**GET** `/api/passes?satellite=CARTOSAT-3&hours=24`

Returns all computed passes + AI-recommended best pass.

#### Example
```bash
curl "http://127.0.0.1:5000/api/passes?satellite=CARTOSAT-3&hours=24"
```

---

### 5. Analyze Telemetry / Simulate Fault
**GET** `/api/anomaly?satellite=CARTOSAT-3&fault=battery_fault`

If `fault` is omitted, the system generates **normal telemetry**.

#### Example
```bash
curl "http://127.0.0.1:5000/api/anomaly?satellite=CARTOSAT-3&fault=battery_fault"
```

Supported fault examples:
- `battery_fault`
- `overheating`
- `attitude_fault`
- `memory_leak`

---

### 6. Plan EO Imaging Task
**POST** `/api/eo-plan`

#### Example Request
```json
{
  "satellite": "SENTINEL-2A",
  "region": "Assam, India",
  "objective": "flood monitoring",
  "area_sq_km": 5000
}
```

#### Example cURL
```bash
curl -X POST http://127.0.0.1:5000/api/eo-plan \
  -H "Content-Type: application/json" \
  -d "{\"satellite\":\"SENTINEL-2A\",\"region\":\"Assam, India\",\"objective\":\"flood monitoring\",\"area_sq_km\":5000}"
```

---

### 7. Run Full Mission Workflow
**POST** `/api/mission`

Runs:
- Pass Scheduler
- Anomaly Detector
- EO Task Planner
- Final Mission Summary

#### Example Request
```json
{
  "satellite": "CARTOSAT-3",
  "region": "Punjab, India",
  "objective": "crop health monitoring",
  "fault": null
}
```

#### Example cURL
```bash
curl -X POST http://127.0.0.1:5000/api/mission \
  -H "Content-Type: application/json" \
  -d "{\"satellite\":\"CARTOSAT-3\",\"region\":\"Punjab, India\",\"objective\":\"crop health monitoring\",\"fault\":null}"
```

---

## 🧪 Example Use Cases

### Normal Mission Scenario
- Satellite: `CARTOSAT-3`
- Objective: `crop health monitoring`
- Region: `Punjab, India`

**Expected flow:**
1. Compute next 24h passes over Hyderabad ground station
2. Recommend best pass for downlink
3. Confirm telemetry is nominal
4. Plan EO imaging for crop health
5. Return **GO** or **CAUTION** mission status

---

### Emergency Fault Scenario
- Satellite: `SENTINEL-2A`
- Objective: `flood monitoring`
- Region: `Assam, India`
- Fault: `battery_fault`

**Expected flow:**
1. Compute passes
2. Inject battery-related telemetry anomaly
3. Detect likely power subsystem issue
4. Escalate to operator if severity is `CRITICAL`
5. Return **CAUTION** or **NO-GO** mission status

---

## 🧠 Design Philosophy

This project follows a **hybrid AI architecture**:

- **Deterministic logic first** for reliability  
  (orbital calculations, threshold checks, known satellite capabilities)

- **LLM reasoning second** for decision support  
  (best-pass selection, anomaly interpretation, mission planning, operator briefing)

- **Human-in-the-loop guardrails** for safety  
  (low-confidence or critical outputs trigger review)

This makes the system more realistic for **space operations**, where AI should **assist operators**, not blindly replace them.

---

## 🔒 Safety / Guardrails

The system includes lightweight operational safeguards:

- **Threshold checks before LLM calls** to reduce hallucination risk
- **Confidence-based escalation** when outputs are uncertain
- **Human review required** for:
  - low-confidence decisions
  - critical anomaly classifications
- **Structured JSON-only LLM prompts** for reliable downstream parsing

---

## 📌 Current Limitations

- Uses a **fixed ground station** (`Dhruva Space HQ, Hyderabad`) in the pass scheduler
- EO planning uses a **small built-in satellite capability knowledge base** (not full mission specs)
- Telemetry is **simulated**, not streamed from real spacecraft systems
- LLM outputs are structured but still depend on API reliability
- No persistent storage / mission history yet
- No frontend dashboard included in this repository (API-only backend)

---

## 🔮 Future Improvements

Planned / possible next steps:

- [ ] Add **RAG-based satellite capability retrieval** from mission docs
- [ ] Integrate **real telemetry streams** or replay logs
- [ ] Support **multiple ground stations**
- [ ] Add **satellite visibility maps**
- [ ] Add **mission history + database storage**
- [ ] Build a **React mission control dashboard**
- [ ] Add **LangGraph-based agent state flow visualization**
- [ ] Integrate **space weather / conjunction risk checks**
- [ ] Add **SAR satellite support** for cloud-penetrating EO planning

---

## 🎯 Why This Project Matters

Modern satellite operations involve:
- scheduling communication windows
- monitoring spacecraft health
- planning observation tasks under time constraints

This project shows how **AI agents can be used as decision-support copilots** in mission operations by combining:

- orbital data
- telemetry analysis
- mission planning
- operator-friendly summaries

It is especially relevant for:
- **Space AI**
- **Mission operations automation**
- **EO tasking systems**
- **Agentic workflows for aerospace**

---

## 🤝 Contributing

Contributions, ideas, and improvements are welcome.

If you'd like to extend the project:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a pull request

---

## 📜 License

MIT License

---

## 👩‍💻 Author

**Shruthi G**  
AI/ML + Space Systems Enthusiast  
Building projects at the intersection of **AI, Earth Observation, and Satellite Operations**

GitHub: [Shruthi280](https://github.com/Shruthi280)

---

## ⭐ If you like this project

If this project interests you, consider:
- starring the repo ⭐
- sharing feedback
- suggesting new space mission workflows
- collaborating on AI-for-space ideas 🚀

---

## 📷 Suggested Demo Screenshots (Optional)

You can improve this README further by adding:
- API response screenshots
- sample JSON mission output
- architecture diagram
- Postman collection screenshots
- future frontend dashboard preview

---

# 🚀 One-Line Summary

**SatOps AI Agent is a multi-agent mission-control simulation system that uses orbital mechanics + telemetry analysis + LLM reasoning to support smarter LEO satellite operations.**
