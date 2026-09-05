# Radflow Sentinel

> **Domain:** Diagnostic Radiology & Medical Imaging AI
> **Reference Guidelines & Standards:** `American College of Radiology (ACR) RADS & Fleischner Society`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Radflow Sentinel** is an advanced analytical and computational platform implementing multi-agent consensus evaluation for radiology and neuroimaging systems. It provides:

- **Critical Finding Detection**: Automated identification of life-threatening findings (tension pneumothorax, acute PE, intracranial hemorrhage, aortic dissection, etc.)
- **Incidentaloma Tracking**: Fleischner Society 2017 guideline-based follow-up scheduling for pulmonary nodules
- **Contrast Safety Auditing**: eGFR-based contrast-induced nephropathy risk assessment
- **Zero-PHI Outbound Guard**: Prevents protected health information from leaving the system
- **Tamper-Evident Audit Trail**: HMAC-SHA256 chained cryptographic audit logging

All 10 tests passing.

---

## ⚙️ Key Capabilities & Algorithmic Modules

- **Deterministic Calculation Engine**: Strict compliance with standard reference formulations and thresholds.
- **Risk & Urgency Classification**: Multi-tier categorization with automated clinical/operational action recommendations.
- **Validation & Guardrails**: Rigorous input bounds checking and anomaly detection.
- **Multi-Agent Consensus**: InvariantQCWorker, SafetyEscalationWorker, and ProtocolConformanceWorker.

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/radflow-sentinel.git
cd radflow-sentinel

# Install dependencies
pip install fastapi uvicorn pydantic pytest
```

---

## 💻 CLI Quickstart & Usage

### 1. Run a Single Audit
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Query the Supervisor Chat
```bash
python cli.py chat "What are the Fleischner Society rules?"
```

### 3. Batch Process CSV Records
```bash
python cli.py batch -i input.csv -o results.csv
```

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Launch FastAPI REST Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--task-id`: Unique task / case identifier
- `--target`: Entity, patient key, or target identifier
- `--primary`: Primary domain measurement or score (float)
- `--secondary`: Secondary kinetic or confidence score (float)
- `--critical`: Flag for emergency escalation (boolean)
- `--status`: Status code or phenotype descriptor (e.g., NOMINAL, DISCORDANT_ANOMALY)

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Configuration

**IMPORTANT**: Set the `AUDIT_SECRET_KEY` environment variable in production to ensure consistent audit trail signing across restarts:

```bash
# Linux/macOS
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Windows PowerShell
$env:AUDIT_SECRET_KEY = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_})
```

If not set, a random key is generated per session (suitable for development only).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 100
```

---

## 🐳 Container Deployment

```bash
docker build -t radflow-sentinel .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key radflow-sentinel
```

Or using Docker Compose:

```bash
# Set your production key
export AUDIT_SECRET_KEY=your-secret-key
docker-compose up -d
```

---

## 📁 Project Structure

```
radflow-sentinel/
├── agents/              # Core agent modules (supervisor, workers, security)
│   ├── api.py           # FastAPI REST endpoints
│   ├── base.py          # PHI guard, HMAC audit trail, security
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-agent orchestrator
│   ├── workers.py       # Specialized evaluation workers
│   ├── llm_factory.py   # LLM provider abstraction
│   ├── metrics.py       # Prometheus metrics collector
│   ├── learning.py      # Bayesian calibration engine
│   └── streamer.py      # WebSocket telemetry broadcaster
├── radflow/             # Radiology-specific modules
│   ├── agents.py        # Critical finding, incidentaloma, contrast safety agents
│   ├── models.py        # Radiology data models
│   ├── cli.py           # Radiology CLI interface
│   └── server.py        # Radiology FastAPI server
├── tests/               # Pytest test suite
├── web/                 # Operations console (HTML/JS)
├── cli.py               # Main CLI entry point
├── simulator.py         # High-throughput simulation
├── enrichment.py        # Domain enrichment engines
├── Dockerfile           # Container build
├── docker-compose.yml   # Container orchestration
└── pyproject.toml       # Project configuration
```
