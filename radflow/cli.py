"""
CLI for RadFlow Sentinel.
"""

import argparse
import json
import os
import sys
from .models import RadiologyReport
from .agents import SentinelCoordinator


def get_sample_report() -> RadiologyReport:
    return RadiologyReport(
        report_id="RAD-2026-9041",
        accession_number="ACC-5521",
        patient_id="PT-RAD-3312",
        exam_type="CT Chest with IV Contrast (PE Protocol)",
        findings_text=(
            "Large occlusive filling defect identified within the main right pulmonary artery extending into the right interlobar artery. "
            "Right ventricular to left ventricular diameter ratio is 1.2, suggesting acute right heart strain. "
            "Additionally, an incidental 7 mm solid non-calcified nodule is noted in the right upper lobe (Series 3, Image 44)."
        ),
        impression_text=(
            "1. ACUTE PULMONARY EMBOLISM involving right main and lobar branches with CT evidence of right heart strain.\n"
            "2. Incidental 7 mm solid right upper lobe pulmonary nodule."
        ),
        patient_egfr=48.0,
        ordering_provider="Dr. Sarah Jenkins (Emergency Medicine)",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="radflow",
        description="Autonomous Radiology Critical Finding Escalation & Incidentaloma Tracking Agent.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Audit radiology report narrative")
    audit_parser.add_argument("-r", "--report-json", default=None, help="Path to report JSON")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Query air-gapped radiology assistant")
    chat_parser.add_argument("query", nargs="+", help="Natural language query")

    # Sample command
    sample_parser = subparsers.add_parser("sample", help="Export sample radiology report JSON")
    sample_parser.add_argument("-o", "--output", default=None, help="Output file path")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    serve_parser.add_argument("--port", type=int, default=8004, help="Port")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind address")

    args = parser.parse_args(argv)
    coordinator = SentinelCoordinator()

    if args.command == "sample":
        rep = get_sample_report()
        rep_dict = {
            "report_id": rep.report_id,
            "accession_number": rep.accession_number,
            "patient_id": rep.patient_id,
            "exam_type": rep.exam_type,
            "findings_text": rep.findings_text,
            "impression_text": rep.impression_text,
            "patient_egfr": rep.patient_egfr,
            "ordering_provider": rep.ordering_provider,
        }
        json_str = json.dumps(rep_dict, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"Sample report written to: {args.output}")
        else:
            print(json_str)
        return 0

    if args.command == "audit":
        if args.report_json:
            with open(args.report_json, "r", encoding="utf-8") as f:
                d = json.load(f)
            rep = RadiologyReport(
                report_id=d["report_id"],
                accession_number=d["accession_number"],
                patient_id=d["patient_id"],
                exam_type=d["exam_type"],
                findings_text=d["findings_text"],
                impression_text=d["impression_text"],
                patient_egfr=d.get("patient_egfr"),
                ordering_provider=d.get("ordering_provider", "Dr. Provider"),
            )
        else:
            rep = get_sample_report()

        dossier = coordinator.audit_report(rep)

        print("=" * 80)
        print(f"  RADFLOW SENTINEL RADIOLOGY SURVEILLANCE: {dossier['report_id']}")
        print(f"  Exam: {dossier['exam_type']} | Status: [{dossier['overall_status']}]")
        print(f"  Closed-Loop Verbal Notification Required: {dossier['closed_loop_notification_required']}")
        print("=" * 80)

        for a in dossier["alerts"]:
            print(f"\n  [{a['urgency']}] {a['title']}")
            print(f"  Finding: {a['finding']}")
            print(f"  Action: {a['action']}")
            if a["incidental_followup"]:
                fol = a["incidental_followup"]
                print(f"  -> Incidental Schedule: {fol['organ']} | Due: {fol['target_date']} ({fol['interval_months']} mo) | Standard: {fol['guideline']}")

        print("\n" + "=" * 80)
        return 0

    if args.command == "serve":
        if args.host not in ("127.0.0.1", "localhost", "::1") and not os.getenv("RADFLOW_API_TOKEN"):
            parser.error("RADFLOW_API_TOKEN is required for non-loopback API binding")
        from .server import create_app
        import uvicorn
        app = create_app()
        if app is None:
            parser.error("FastAPI and Pydantic must be installed: pip install -e '.[api]'")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    if args.command == "chat":
        ans = coordinator.query_assistant(" ".join(args.query))
        print(f"\n[RadFlow Assistant]:\n{ans}\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
