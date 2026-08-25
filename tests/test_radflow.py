import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from radflow.models import RadiologyReport, FindingUrgency
from radflow.agents import (
    AcuteCriticalFinderAgent,
    IncidentalomaTrackerAgent,
    ContrastSafetyAuditorAgent,
    SentinelCoordinator,
)
from radflow.cli import main


def test_acute_critical_finder():
    agent = AcuteCriticalFinderAgent()
    rep = RadiologyReport(
        report_id="R-01",
        accession_number="A-01",
        patient_id="P-01",
        exam_type="CT Chest",
        findings_text="There is a large tension pneumothorax on the right with mediastinal shift.",
        impression_text="1. Tension pneumothorax.",
    )
    alerts = agent.evaluate(rep)
    assert len(alerts) >= 1
    assert alerts[0].urgency == FindingUrgency.STAT_RED_ALERT
    assert alerts[0].closed_loop_required is True


def test_incidentaloma_tracker():
    agent = IncidentalomaTrackerAgent()
    rep = RadiologyReport(
        report_id="R-02",
        accession_number="A-02",
        patient_id="P-02",
        exam_type="CT Abdomen",
        findings_text="Incidental 6 mm pulmonary nodule at the lung base.",
        impression_text="6 mm lung nodule.",
    )
    alerts = agent.evaluate(rep)
    assert len(alerts) >= 1
    assert alerts[0].urgency == FindingUrgency.INCIDENTAL_FOLLOWUP
    assert alerts[0].incidental_tracking.recommended_interval_months == 6


def test_contrast_safety_auditor():
    agent = ContrastSafetyAuditorAgent()
    rep = RadiologyReport(
        report_id="R-03",
        accession_number="A-03",
        patient_id="P-03",
        exam_type="CT with IV Contrast",
        findings_text="Normal scan.",
        impression_text="Normal.",
        patient_egfr=22.0,
    )
    alerts = agent.evaluate(rep)
    assert len(alerts) == 1
    assert alerts[0].urgency == FindingUrgency.URGENT_NON_CRITICAL


def test_sentinel_coordinator():
    coord = SentinelCoordinator()
    rep = RadiologyReport(
        report_id="R-04",
        accession_number="A-04",
        patient_id="P-04",
        exam_type="MRI Brain",
        findings_text="Acute subarachnoid hemorrhage along the basal cisterns.",
        impression_text="Acute SAH.",
    )
    dossier = coord.audit_report(rep)
    assert dossier["overall_status"] == "STAT_CRITICAL_ALERT"
    assert dossier["closed_loop_notification_required"] is True

    ans = coord.query_assistant("What are the Fleischner Society rules?")
    assert "Fleischner" in ans


def test_cli():
    assert main(["audit"]) == 0
    assert main(["chat", "What", "is", "a", "critical", "finding?"]) == 0
