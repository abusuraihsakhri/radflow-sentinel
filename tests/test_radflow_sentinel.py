"""
Automated Pytest Test Suite for Radflow Sentinel.
Domain: Radiology & Neuroimaging Systems
Standard: ACR RADS / Fleischner Society / ASPECTS Guidelines
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import math
import pytest
from agents.base import PHIGuard, AuditLogger, AuditTrail, SecurityException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_nan_infinity_rejection():
    """Security: NaN and Infinity values must be rejected."""
    with pytest.raises(Exception):
        SystemTaskPayload(task_id="T-NAN", target_identifier="K1", primary_metric=math.nan)
    with pytest.raises(Exception):
        SystemTaskPayload(task_id="T-INF", target_identifier="K1", primary_metric=math.inf)
    with pytest.raises(Exception):
        SystemTaskPayload(timeout="T-INF", target_identifier="K1", primary_metric=1.0, secondary_metric=-math.inf)


def test_batch_csv_boolean_parsing():
    """Security: Batch CSV boolean parsing must handle string values correctly."""
    import tempfile
    import os
    import csv

    # Create a test CSV with various boolean representations
    test_csv = "task_id,target_identifier,primary_metric,secondary_metric,status_descriptor,is_critical_flag\n"
    test_csv += "T1,K1,10.0,5.0,NOMINAL,false\n"
    test_csv += "T2,K2,10.0,5.0,NOMINAL,0\n"
    test_csv += "T3,K3,10.0,5.0,NOMINAL,no\n"
    test_csv += "T4,K4,10.0,5.0,NOMINAL,true\n"
    test_csv += "T5,K5,10.0,5.0,NOMINAL,1\n"
    test_csv += "T6,K6,10.0,5.0,NOMINAL,yes\n"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write(test_csv)
        input_path = f.name

    output_path = input_path + '.out.csv'

    try:
        result = main(["batch", "-i", input_path, "-o", output_path])
        assert result == 0

        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 6
        # "false", "0", "no" should NOT be critical
        assert rows[0]["overall_urgency"] == "ROUTINE"
        assert rows[1]["overall_urgency"] == "ROUTINE"
        assert rows[2]["overall_urgency"] == "ROUTINE"
        # "true", "1", "yes" SHOULD be critical (secondary_metric=5.0 < 12.0 but is_critical_flag=True triggers SafetyEscalationWorker)
        assert rows[3]["overall_urgency"] == "CRITICAL_STAT_PANIC"
        assert rows[4]["overall_urgency"] == "CRITICAL_STAT_PANIC"
        assert rows[5]["overall_urgency"] == "CRITICAL_STAT_PANIC"
    finally:
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_audit_trail_uses_random_key_by_default():
    """Security: AuditTrail should generate a random key when no secret is provided."""
    import os
    # Ensure env var is not set
    old_key = os.environ.pop("AUDIT_SECRET_KEY", None)
    try:
        trail = AuditTrail()
        # Key should be 32 bytes (256 bits) when randomly generated
        assert len(trail.secret_key) == 32
    finally:
        if old_key:
            os.environ["AUDIT_SECRET_KEY"] = old_key


def test_audit_trail_uses_env_var_when_set():
    """Security: AuditTrail should use AUDIT_SECRET_KEY env var when set."""
    import os
    old_key = os.environ.get("AUDIT_SECRET_KEY")
    os.environ["AUDIT_SECRET_KEY"] = "test-secret-key-12345"
    try:
        trail = AuditTrail()
        assert trail.secret_key == b"test-secret-key-12345"
    finally:
        if old_key is None:
            os.environ.pop("AUDIT_SECRET_KEY", None)
        else:
            os.environ["AUDIT_SECRET_KEY"] = old_key

def test_audit_tampering_is_detected():
    trail = AuditTrail(secret_key="test-only-secret")
    entry = trail.log("tester", "supervisor", "AUDIT", {"task_id": "SAFE-01"})
    assert trail.verify_integrity()
    entry["payload_hash"] = "changed"
    assert trail.verify_integrity()  # Returned entry is a copy.
    snapshot = trail.get_trail()
    snapshot[0]["payload_hash"] = "changed"
    assert trail.verify_integrity()  # Returned trail is a copy.
    trail.logs[0]["payload_hash"] = "changed"
    assert not trail.verify_integrity()  # Authenticating each block catches edits.


def test_audit_rejects_phi_in_signed_fields():
    trail = AuditTrail(secret_key="test-only-secret")
    with pytest.raises(SecurityException):
        trail.log("Patient MRN-995577", "supervisor", "AUDIT", {})
