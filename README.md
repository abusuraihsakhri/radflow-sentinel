# Radflow Sentinel

Experimental radiology-report screening and deterministic task-audit utilities, with a separate browser-only demonstrator.

**Research prototype; not validated for clinical use.** Do not enter identifiable patient information or use outputs for diagnosis, treatment, or clinical follow-up decisions.

## Components

| Component | Interface | Behavior |
| --- | --- | --- |
| Radiology screening (radflow/) | Python CLI; optional FastAPI | Keyword screening for selected critical findings, pulmonary nodule follow-up suggestions, low-eGFR contrast protocol review |
| Generic task evaluator (agents/) | Python CLI; optional FastAPI | Three deterministic demonstration workers using fixed numeric and keyword thresholds |
| Local demonstrator (web/) | Static HTML/JavaScript | Browser-only generic threshold examples, session counters and unsigned JSON export |
| Audit chain (agents/base.py) | Python process | HMAC-SHA256 linked records with signature re-verification |

The two Python engines are separate. The browser demo does not execute Python or communicate with the backend.

## Clinical and technical limitations

- Keyword matching is **not validated clinical NLP**. Negation recognition is heuristic; historical, uncertain, or irrelevant mentions can still trigger alerts and true findings may be missed.
- Pulmonary nodule suggestions are conditional illustrations, not a complete implementation of Fleischner eligibility, solid/subsolid, single/multiple nodule, or risk-stratification requirements. Dates represent **suggested follow-up**, not actual scheduled appointments.
- Low-eGFR alerts are prompts for professional contrast protocol review, not treatment instructions.
- Regex-based identifier checks do **not** establish de-identification, HIPAA compliance, or zero-PHI guarantees.
- The HMAC audit chain resides only in process memory. It cannot prove that an entire ledger has not been truncated or deleted and is not a persistent compliance record.
- The repository does not provide live PACS/RIS connectivity, clinician notification, model inference, or real-time telemetry.

## Browser demonstrator

Open web/index.html in a current browser. The page evaluates example thresholds locally, with no network calls, storage, or external dependencies. Use only synthetic IDs. The JSON export is unsigned and is not a clinical audit record.

The GitHub Pages workflow deploys the web/ directory when the repository's Pages source is set to GitHub Actions. The public Pages URL should only be used after the deployment has been verified.

## Install and test

Requires Python 3.9+; the JavaScript tests additionally need Node.js 20+.

    git clone https://github.com/abusuraihsakhri/radflow-sentinel.git
    cd radflow-sentinel
    python -m pip install -e ".[api,dev]"
    python -m pytest -q
    node --check web/app.js
    node --test tests/web.test.cjs
    python -m compileall -q agents radflow cli.py

## Radiology screening CLI

    radflow sample -o sample.json
    radflow audit --report-json sample.json
    radflow audit
    radflow chat "What is the pulmonary nodule rule?"
    radflow serve --host 127.0.0.1 --port 8004

The radiology API provides GET /health, POST /api/reports/audit and POST /api/chat. The sample contains fictional data.

## Generic audit CLI

    python cli.py audit --task-id TEST-001 --target TARGET-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
    python cli.py batch -i input.csv -o results.csv
    python cli.py verify-audit
    python cli.py serve --host 127.0.0.1 --port 8000

Example batch CSV columns: task_id, target_identifier, primary_metric, secondary_metric, status_descriptor, is_critical_flag.

Generic API routes: GET /health, GET /metrics, POST /api/audit, POST /api/chat, GET /api/audit/logs. The /metrics route returns JSON rather than Prometheus exposition text. The generic thresholds (primary >25, secondary >12) are arbitrary software-test rules, **not radiology standards**.

## Security and Docker

Set RADFLOW_API_TOKEN to enable Bearer token authentication for API routes, using the Authorization HTTP header. The CLIs refuse non-loopback binds without a token. Directly binding the ASGI app with a third-party server can bypass the CLI check and must not be done without appropriate access control. A production system additionally needs TLS, durable logging, authorization, privacy review and operational controls.

Set a long random AUDIT_SECRET_KEY for repeatable signature verification during a process lifetime. Without it, a random per-process key is generated. Setting a key does not make the log persistent.

    cp .env.example .env
    # Edit .env: set long, unique secrets for both required variables.
    docker compose up --build
    curl http://127.0.0.1:8000/health

Docker Compose binds localhost by default and requires both secrets. Never commit .env.

## Technology, compatibility and license

Python, Pydantic v2, optional FastAPI/Uvicorn, HTML/CSS/vanilla JavaScript, Node's built-in test runner, GitHub Actions. The browser page is designed for current Chromium, Firefox and Safari, without external fonts or scripts. The API's autogenerated /docs reflects the live schema; the checked-in openapi_spec.json is a legacy snapshot.

[MIT License](LICENSE).
