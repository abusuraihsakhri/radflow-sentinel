"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { evaluateAudit } = require("../web/app.js");

const base = {
  task_id: "TASK-01", target_identifier: "TARGET-01",
  primary_metric: 10, secondary_metric: 5,
  status_descriptor: "NOMINAL", is_critical_flag: false
};

test("routine task", () => {
  const out = evaluateAudit(base);
  assert.equal(out.overall_urgency, "ROUTINE");
  assert.equal(out.total_alerts, 0);
  assert.equal(out.audit_signature, null);
});

test("elevated metrics match Python worker thresholds", () => {
  const out = evaluateAudit({ ...base, primary_metric: 25.1, secondary_metric: 12.1 });
  assert.equal(out.overall_urgency, "ELEVATED_RISK");
  assert.equal(out.total_alerts, 2);
});

test("critical flag dominates all other thresholds", () => {
  const out = evaluateAudit({ ...base, is_critical_flag: true });
  assert.equal(out.overall_urgency, "CRITICAL_STAT_PANIC");
  assert.equal(out.integrity_status, "RECALIBRATION_REQUIRED");
});

test("status descriptor can raise an anomaly alert", () => {
  const out = evaluateAudit({ ...base, status_descriptor: "DISCORDANT_ANOMALY" });
  assert.equal(out.total_alerts, 1);
});

test("nonfinite, missing and identifying inputs are rejected", () => {
  assert.throws(() => evaluateAudit({ ...base, primary_metric: Infinity }), /finite/);
  assert.throws(() => evaluateAudit({ ...base, primary_metric: "" }), /required/);
  assert.throws(() => evaluateAudit({ ...base, target_identifier: "MRN-123456" }), /identifying/);
  assert.throws(() => evaluateAudit({ ...base, task_id: "a@hospital.org" }), /identifying/);
});
