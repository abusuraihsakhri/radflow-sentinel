"use strict";

/* Static demonstrator of the threshold rules in agents/workers.py.
   This file makes no network requests and must not be used for clinical care. */
(function () {
  const suspectIdentifier = [
    /\bMRN\s*[:# -]*\d{4,10}\b/i,
    /\b\d{3}-\d{2}-\d{4}\b/,
    /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
    /\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b/
  ];

  function evaluateAudit(input) {
    const taskId = String(input.task_id || "").trim();
    const targetId = String(input.target_identifier || "").trim();
    const descriptor = String(input.status_descriptor || "NOMINAL").trim();
    if (!taskId || !targetId || taskId.length > 80 || targetId.length > 80 ||
        descriptor.length > 100) {
      throw new Error("Provide valid synthetic identifiers (maximum 80 characters each).");
    }
    if ([taskId, targetId, descriptor].some(function (s) {
      return suspectIdentifier.some(function (p) { return p.test(s); });
    })) {
      throw new Error("Possible identifying information detected. Use synthetic IDs only.");
    }

    if (input.primary_metric === "" || input.secondary_metric === "" ||
        input.primary_metric == null || input.secondary_metric == null) {
      throw new Error("Both metric fields are required.");
    }
    const primary = Number(input.primary_metric);
    const secondary = Number(input.secondary_metric);
    if (!Number.isFinite(primary) || !Number.isFinite(secondary)) {
      throw new Error("Metric fields must be finite numbers.");
    }

    const alerts = [];
    if (primary > 25) {
      alerts.push({
        origin_worker: "InvariantQCWorker",
        urgency: "ELEVATED_RISK",
        summary: "Primary metric threshold exceeded (25)."
      });
    }
    if (input.is_critical_flag === true || secondary > 12) {
      alerts.push({
        origin_worker: "SafetyEscalationWorker",
        urgency: input.is_critical_flag === true ? "CRITICAL_STAT_PANIC" : "ELEVATED_RISK",
        summary: "Demo critical flag or secondary threshold (12) triggered."
      });
    }
    if (["DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT"].some(function (word) {
      return descriptor.toUpperCase().includes(word);
    })) {
      alerts.push({
        origin_worker: "ProtocolConformanceWorker",
        urgency: "ELEVATED_RISK",
        summary: "Status descriptor matched a demo anomaly keyword."
      });
    }

    const critical = alerts.some(function (a) { return a.urgency === "CRITICAL_STAT_PANIC"; });
    const elevated = alerts.length > 0;
    const urgency = critical ? "CRITICAL_STAT_PANIC" : elevated ? "ELEVATED_RISK" : "ROUTINE";
    return {
      system_slug: "radflow-sentinel",
      mode: "local-unverified-demonstration",
      task_id: taskId,
      target_identifier: targetId,
      overall_urgency: urgency,
      integrity_status: critical ? "RECALIBRATION_REQUIRED" :
        elevated ? "DISCORDANT_ANOMALY" : "VALIDATED_OPTIMAL",
      total_alerts: alerts.length,
      alerts: alerts,
      audit_signature: null,
      clinical_validity: "not validated"
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { evaluateAudit: evaluateAudit };
  }

  if (typeof document === "undefined") {
    return;
  }

  function byId(id) { return document.getElementById(id); }
  const form = byId("audit-form");
  const output = byId("outputConsole");
  const notice = byId("notice");
  const exportButton = byId("export-btn");
  let latest = null;
  let tasks = 0;
  let alerts = 0;
  let rejected = 0;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    try {
      latest = evaluateAudit({
        task_id: byId("task_id").value,
        target_identifier: byId("target_id").value,
        primary_metric: byId("primary_metric").value,
        secondary_metric: byId("secondary_metric").value,
        status_descriptor: byId("status_descriptor").value,
        is_critical_flag: byId("is_critical").checked
      });
      tasks += 1;
      alerts += latest.total_alerts;
      byId("m-tasks").textContent = String(tasks);
      byId("m-alerts").textContent = String(alerts);
      output.textContent = JSON.stringify(latest, null, 2);
      notice.textContent = "Local evaluation complete. No data transmitted.";
      exportButton.disabled = false;
    } catch (error) {
      latest = null;
      rejected += 1;
      byId("m-blocks").textContent = String(rejected);
      output.textContent = "No dossier generated.";
      notice.textContent = error.message;
      exportButton.disabled = true;
    }
  });

  form.addEventListener("reset", function () {
    latest = null;
    exportButton.disabled = true;
    output.textContent = "No evaluation performed.";
    notice.textContent = "Inputs reset. Session counters are unchanged.";
  });

  exportButton.addEventListener("click", function () {
    if (!latest) return;
    const objectUrl = URL.createObjectURL(new Blob(
      [JSON.stringify(latest, null, 2) + "\n"], { type: "application/json" }
    ));
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = "radflow-demonstration.json";
    anchor.click();
    window.setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 1000);
  });
}());
