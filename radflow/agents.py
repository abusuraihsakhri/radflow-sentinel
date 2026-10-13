"""
RadFlow Sentinel Distributed Component Radiology Escalation & Incidentaloma Hierarchy.
"""

import re
import math
import uuid
import datetime
from typing import List, Dict, Any, Optional
from .models import (
    RadiologyReport,
    SentinelAlert,
    FindingUrgency,
    IncidentalTrackingEntry,
)

def _is_negated(text: str, start: int) -> bool:
    """Avoid obvious negative findings; this is not clinical NLP validation."""
    prefix = text[max(0, start - 100):start].lower()
    prefix = re.split(r"[.;\n]|\b(?:but|however|although)\b", prefix)[-1]
    return bool(re.search(
        r"\b(?:no|without|negative\s+for|absence\s+of|free\s+of|"
        r"ruled\s+out|excluded)\b(?:\W+\w+){0,6}\W*$",
        prefix
    ))


CRITICAL_FINDING_PATTERNS = [
    (r"\b(tension\s+pneumothorax|large\s+pneumothorax)\b", "Tension / Large Pneumothorax", "Immediate clinical assessment and closed-loop notification per local protocol."),
    (r"\b(pulmonary\s+embolism|pulmonary\s+embolus|saddle\s+embolus|acute\s+pe)\b", "Acute Pulmonary Embolism", "Urgent clinical evaluation and direct closed-loop notification per local critical-result protocol."),
    (r"\b(intracranial\s+hemorrhage|subdural\s+hematoma|subarachnoid\s+hemorrhage|epidural\s+hematoma|intracerebral\s+hemorrhage)\b", "Acute Intracranial Hemorrhage", "Urgent neurosurgical consultation and blood pressure / reversal management."),
    (r"\b(aortic\s+dissection|intramural\s+hematoma\s+aorta)\b", "Acute Aortic Dissection", "Urgent specialist evaluation and direct closed-loop notification per local protocol."),
    (r"\b(pneumoperitoneum|free\s+intraperitoneal\s+air|perforated\s+viscus)\b", "Pneumoperitoneum / Viscus Perforation", "Emergency surgical consult for exploratory laparotomy/laparoscopy."),
    (r"\b(testicular\s+torsion|ovarian\s+torsion)\b", "Acute Gonadal Torsion", "Immediate urology / gynecology emergent operative detorsion."),
]


class AcuteCriticalFinderAgent:
    """
    Scans report narratives for life-threatening acute findings requiring mandatory closed-loop verbal escalation.
    """
    def evaluate(self, report: RadiologyReport) -> List[SentinelAlert]:
        alerts = []
        combined_text = f"{report.findings_text} {report.impression_text}".lower()

        for pattern, finding_title, action in CRITICAL_FINDING_PATTERNS:
            match = re.search(pattern, combined_text)
            if match and not _is_negated(combined_text, match.start()):
                alerts.append(
                    SentinelAlert(
                        alert_id=str(uuid.uuid4())[:8],
                        report_id=report.report_id,
                        patient_id=report.patient_id,
                        urgency=FindingUrgency.STAT_RED_ALERT,
                        title=f"CRITICAL RED ALERT: {finding_title}",
                        clinical_finding=f"Pattern detected: '{match.group(0)}' in {report.exam_type}.",
                        closed_loop_required=True,
                        remediation_action=action,
                    )
                )

        return alerts


class IncidentalomaTrackerAgent:
    """
    Applies Fleischner Society 2017 & ACR White Paper consensus guidelines for follow-up scheduling.
    """
    def evaluate(self, report: RadiologyReport) -> List[SentinelAlert]:
        alerts = []
        combined_text = f"{report.findings_text} {report.impression_text}".lower()

        # Pulmonary nodule detection (Fleischner 2017)
        nodule_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*mm\b"
            r"(?:[\s-]+(?:solid|non-calcified|noncalcified|pulmonary|lung|"
            r"subpleural|right|left|upper|middle|lower|lobe|solitary|single)){0,7}"
            r"\s+nodule\b",
            combined_text,
        )
        nearby = combined_text[max(0, nodule_match.start() - 90):nodule_match.end() + 100] if nodule_match else ""
        pulmonary_context = bool(re.search(r"\b(?:lung|pulmonary|pleural|lobe|chest)\b", nearby)) or "chest" in report.exam_type.lower()
        if nodule_match and pulmonary_context and not _is_negated(combined_text, nodule_match.start()):
            size_mm = float(nodule_match.group(1))
            if size_mm < 6.0:
                interval_mo = 12
                desc = f"Small pulmonary nodule (<6 mm, measure: {size_mm:.0f} mm)"
                rec = "Optional follow-up at 12 months for high-risk patients per Fleischner 2017."
            elif size_mm <= 8.0:
                interval_mo = 6
                desc = f"Intermediate pulmonary nodule (6-8 mm, measure: {size_mm:.0f} mm)"
                rec = "Follow-up low-dose CT Chest recommended in 6-12 months per Fleischner 2017."
            else:
                interval_mo = 3
                desc = f"Large pulmonary nodule (>8 mm, measure: {size_mm:.0f} mm)"
                rec = "Consider CT at 3 months, PET-CT, or tissue biopsy per Fleischner 2017."

            try:
                study_date = datetime.datetime.fromisoformat(report.study_datetime.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                study_date = datetime.datetime.now(datetime.timezone.utc)
            target_date = (study_date + datetime.timedelta(days=interval_mo * 30)).strftime("%Y-%m-%d")

            incidental_entry = IncidentalTrackingEntry(
                organ_system="Lung",
                finding_description=desc,
                guideline_applied="Fleischner Society 2017",
                recommended_modality="Low-dose non-contrast CT Chest",
                recommended_interval_months=interval_mo,
                target_followup_date=target_date,
            )

            alerts.append(
                SentinelAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    report_id=report.report_id,
                    patient_id=report.patient_id,
                    urgency=FindingUrgency.INCIDENTAL_FOLLOWUP,
                    title=f"Incidental Lung Nodule: Follow-Up Review ({size_mm:.0f} mm)",
                    clinical_finding=desc,
                    closed_loop_required=False,
                    remediation_action=rec,
                    incidental_tracking=incidental_entry,
                )
            )

        return alerts


class ContrastSafetyAuditorAgent:
    """
    Audits renal safety for IV iodinated and gadolinium contrast administration.
    """
    def evaluate(self, report: RadiologyReport) -> List[SentinelAlert]:
        alerts = []
        if "contrast" in report.exam_type.lower() and report.patient_egfr is not None:
            if not math.isfinite(report.patient_egfr) or not 0 <= report.patient_egfr <= 200:
                raise ValueError("patient_egfr must be within 0–200 mL/min/1.73 m²")
            if report.patient_egfr < 30.0:
                alerts.append(
                    SentinelAlert(
                        alert_id=str(uuid.uuid4())[:8],
                        report_id=report.report_id,
                        patient_id=report.patient_id,
                        urgency=FindingUrgency.URGENT_NON_CRITICAL,
                        title="Low eGFR: Contrast Protocol Review",
                        clinical_finding=f"Patient eGFR is {report.patient_egfr:.1f} mL/min/1.73m² on contrast examination.",
                        closed_loop_required=False,
                        remediation_action="Review contrast agent, acute kidney injury status, patient-specific risk, and current institutional/ACR contrast protocols; do not automatically withhold therapy.",
                    )
                )
        return alerts


class SentinelCoordinator:
    """
    Central orchestrator for Radiology Escalation & Incidental Tracking.
    """
    def __init__(self):
        self.critical_agent = AcuteCriticalFinderAgent()
        self.incidental_agent = IncidentalomaTrackerAgent()
        self.contrast_agent = ContrastSafetyAuditorAgent()
        self.report_registry: Dict[str, Dict[str, Any]] = {}

    def audit_report(self, report: RadiologyReport) -> Dict[str, Any]:
        all_alerts: List[SentinelAlert] = []
        all_alerts.extend(self.critical_agent.evaluate(report))
        all_alerts.extend(self.incidental_agent.evaluate(report))
        all_alerts.extend(self.contrast_agent.evaluate(report))

        has_stat = any(a.urgency == FindingUrgency.STAT_RED_ALERT for a in all_alerts)
        has_urgent = any(a.urgency == FindingUrgency.URGENT_NON_CRITICAL for a in all_alerts)
        has_incidental = any(a.urgency == FindingUrgency.INCIDENTAL_FOLLOWUP for a in all_alerts)

        dossier = {
            "report_id": report.report_id,
            "accession_number": report.accession_number,
            "patient_id": report.patient_id,
            "exam_type": report.exam_type,
            "overall_status": ("STAT_CRITICAL_ALERT" if has_stat else
                               "URGENT_REVIEW_REQUIRED" if has_urgent else
                               "INCIDENTAL_TRACKING_ACTIVE" if has_incidental else
                               "ROUTINE_NORMAL"),
            "closed_loop_notification_required": has_stat,
            "total_alerts": len(all_alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "urgency": a.urgency.value,
                    "title": a.title,
                    "finding": a.clinical_finding,
                    "action": a.remediation_action,
                    "incidental_followup": (
                        {
                            "organ": a.incidental_tracking.organ_system,
                            "interval_months": a.incidental_tracking.recommended_interval_months,
                            "target_date": a.incidental_tracking.target_followup_date,
                            "guideline": a.incidental_tracking.guideline_applied,
                        }
                        if a.incidental_tracking else None
                    ),
                }
                for a in all_alerts
            ],
        }

        self.report_registry[report.report_id] = dossier
        return dossier

    def query_assistant(self, user_query: str) -> str:
        q = user_query.strip().lower()
        if "fleischner" in q or "nodule" in q:
            return "Fleischner Society 2017: Solid single nodules <6 mm require no routine follow-up in low-risk patients; 6-8 mm nodules require CT at 6-12 months; >8 mm nodules require CT at 3 months, PET-CT, or biopsy."
        elif "critical" in q or "red alert" in q:
            return "Example critical findings warrant immediate closed-loop communication in accordance with the institution's escalation protocol; this keyword screener cannot determine clinical urgency reliably."
        else:
            return "RadFlow Sentinel standing by. Real-time surveillance active across PACS/RIS diagnostic reports."
