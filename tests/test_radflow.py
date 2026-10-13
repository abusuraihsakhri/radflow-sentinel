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

def test_negative_critical_finding_is_not_alerted():
    rep = RadiologyReport(
        report_id="R-NEG", accession_number="A-NEG", patient_id="P-NEG",
        exam_type="CT Chest", findings_text="No evidence of pulmonary embolism.",
        impression_text="No pulmonary embolism and no large pneumothorax.",
    )
    assert AcuteCriticalFinderAgent().evaluate(rep) == []


def test_mixed_negated_and_positive_findings():
    rep = RadiologyReport(
        report_id="R-MIX", accession_number="A-MIX", patient_id="P-MIX",
        exam_type="CT Chest", findings_text="No pulmonary embolism but aortic dissection is present.",
        impression_text="Aortic dissection.",
    )
    alerts = AcuteCriticalFinderAgent().evaluate(rep)
    assert any("Dissection" in alert.title for alert in alerts)
    assert not any("Embolism" in alert.title for alert in alerts)


def test_sample_solid_nodule_detection_and_study_date():
    rep = RadiologyReport(
        report_id="R-NOD", accession_number="A-NOD", patient_id="P-NOD",
        exam_type="CT Chest", findings_text="Incidental 7 mm solid non-calcified nodule in the right upper lobe.",
        impression_text="", study_datetime="2025-01-01T00:00:00+00:00",
    )
    alerts = IncidentalomaTrackerAgent().evaluate(rep)
    assert len(alerts) == 1
    assert alerts[0].incidental_tracking.recommended_interval_months == 6
    assert alerts[0].incidental_tracking.target_followup_date == "2025-07-01"


def test_negative_nodule_and_nonlung_nodule_not_tracked():
    rep = RadiologyReport(
        report_id="R-THY", accession_number="A-THY", patient_id="P-THY",
        exam_type="CT Neck", findings_text="No 6 mm pulmonary nodule. 6 mm thyroid nodule.",
        impression_text="",
    )
    assert IncidentalomaTrackerAgent().evaluate(rep) == []


def test_urgent_contrast_warning_is_not_routine():
    rep = RadiologyReport(
        report_id="R-LOW", accession_number="A-LOW", patient_id="P-LOW",
        exam_type="CT with IV Contrast", findings_text="No acute abnormality.",
        impression_text="Normal.", patient_egfr=20,
    )
    dossier = SentinelCoordinator().audit_report(rep)
    assert dossier["overall_status"] == "URGENT_REVIEW_REQUIRED"
