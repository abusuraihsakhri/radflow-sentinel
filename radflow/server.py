"""
FastAPI Server for RadFlow Sentinel.
"""

from typing import Dict, Any, Optional
from .models import RadiologyReport
from .agents import SentinelCoordinator

coordinator = SentinelCoordinator()


def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel

        app = FastAPI(
            title="RadFlow Sentinel API",
            description="Autonomous Radiology Critical Finding Escalation & Incidentaloma Tracking Agent",
            version="1.0.0",
        )

        class AuditReportRequest(BaseModel):
            report_id: str
            accession_number: str
            patient_id: str
            exam_type: str
            findings_text: str
            impression_text: str
            patient_egfr: Optional[float] = None
            ordering_provider: str = "Dr. Provider"

        class ChatRequest(BaseModel):
            query: str

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "RadFlow Sentinel", "version": "1.0.0"}

        @app.post("/api/reports/audit")
        def audit_report(req: AuditReportRequest):
            rep = RadiologyReport(
                report_id=req.report_id,
                accession_number=req.accession_number,
                patient_id=req.patient_id,
                exam_type=req.exam_type,
                findings_text=req.findings_text,
                impression_text=req.impression_text,
                patient_egfr=req.patient_egfr,
                ordering_provider=req.ordering_provider,
            )
            dossier = coordinator.audit_report(rep)
            return dossier

        @app.post("/api/chat")
        def chat(req: ChatRequest):
            return {"response": coordinator.query_assistant(req.query)}

        return app
    except ImportError:
        return None
