"""
FastAPI REST API Server for Radflow Sentinel.
"""
import hmac
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Radflow Sentinel API",
    description="Enterprise Distributed Component Platform (Radiology & Neuroimaging Systems)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


def require_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Require a bearer token when RADFLOW_API_TOKEN is configured."""
    configured = os.getenv("RADFLOW_API_TOKEN")
    if configured and (not authorization or not hmac.compare_digest(
        authorization, "Bearer " + configured
    )):
        raise HTTPException(status_code=401, detail="Authentication required")


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "radflow-sentinel", "domain": "Radiology & Neuroimaging Systems", "standard": "ACR RADS / Fleischner Society / ASPECTS Guidelines", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit", dependencies=[Depends(require_api_token)])
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
        return dossier.to_dict()
    except SecurityException as e:
        raise HTTPException(status_code=400, detail=f"Security violation: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal processing error") from e


@app.post("/api/chat", dependencies=[Depends(require_api_token)])
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Chat query could not be processed") from e


@app.get("/api/audit/logs", dependencies=[Depends(require_api_token)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
