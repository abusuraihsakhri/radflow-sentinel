"""
radflow-sentinel: Data Models & Radiology Follow-Up Classification Catalogs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import datetime


class FindingUrgency(str, Enum):
    ROUTINE = "ROUTINE"
    INCIDENTAL_FOLLOWUP = "INCIDENTAL_FOLLOWUP"
    URGENT_NON_CRITICAL = "URGENT_NON_CRITICAL"
    STAT_RED_ALERT = "STAT_RED_ALERT"  # E.g. Tension PTX, Aortic Dissection, Massive PE, Intracranial Bleed


@dataclass
class RadiologyReport:
    report_id: str
    accession_number: str
    patient_id: str
    exam_type: str              # "CT Chest with IV Contrast", "CT Abdomen/Pelvis", "MRI Brain"
    findings_text: str
    impression_text: str
    patient_egfr: Optional[float] = None
    ordering_provider: str = "Dr. Clinical Provider"
    study_datetime: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


@dataclass
class IncidentalTrackingEntry:
    organ_system: str           # "Lung", "Adrenal", "Thyroid", "Kidney", "Liver"
    finding_description: str    # "6 mm solid non-calcified right upper lobe pulmonary nodule"
    guideline_applied: str      # "Fleischner Society 2017"
    recommended_modality: str   # "Low-dose non-contrast CT Chest"
    recommended_interval_months: int  # 6 to 12 months
    target_followup_date: str


@dataclass
class SentinelAlert:
    alert_id: str
    report_id: str
    patient_id: str
    urgency: FindingUrgency
    title: str
    clinical_finding: str
    closed_loop_required: bool
    remediation_action: str
    incidental_tracking: Optional[IncidentalTrackingEntry] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
