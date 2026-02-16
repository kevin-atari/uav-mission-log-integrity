# UAV Mission Log Integrity System (Tamper-Evident Flight Logs)

This project provides a **tamper-evident mission log pipeline** for UAV operations using:
- cryptographic hashing for integrity,
- chained log entries for tamper detection,
- and optional **anchoring** of a mission digest for auditability.

The goal is **mission assurance**: detecting post-mission log manipulation and improving trust in autonomy telemetry.

> This is not “crypto hype.” It is an engineering-focused integrity and verification system.

---

## What this demonstrates (Engineer I signals)
- System design for integrity and auditability
- Threat modeling: tamper attempts and detection guarantees
- Clear interfaces: log format → hashing → verification → reporting
- Verification discipline: repeatable test cases and measurable outcomes
- Defense-relevant framing: chain-of-custody for autonomy telemetry

---

## System overview
### Inputs
- UAV mission logs (events, timestamps, telemetry samples, metadata)

### Processing
1. Normalize entries into a canonical format
2. Compute per-entry hash
3. Create a hash chain (each entry commits to the prior entry)
4. Compute a mission digest (final commitment)
5. (Optional) anchor mission digest to an immutable external ledger

### Outputs
- Verified report:
  - PASS/FAIL integrity check
  - first detected tamper point (if modified)
  - digest values for audit trails

---

## Threat model (what we detect)
The verifier is designed to detect:
- deleted entries
- edited entries
- reordered entries
- inserted entries (without recomputing the chain)

It does **not** claim to prevent tampering—only to make tampering **detectable** with strong evidence.

---

## Repository structure
- `docs/00_overview.md` — CONOPS-style overview and scope boundaries
- `docs/01_architecture.md` — components, data flow, interfaces
- `docs/05_test_plan.md` — test cases and acceptance criteria
- `docs/06_results.md` — logged runs, artifacts, plots, pass/fail evidence
- `src/` — implementation (to be organized after import)
- `tests/` — verification tests (unit + integration)
- `data/` — sample logs + expected outputs (sanitized)

---

## Attribution & team credit
This repository is a **portfolio-grade continuation and reframing** of a team project originally developed in a university course context.

Original team repository (baseline implementation reference):
- https://github.com/JacobWald/UAVMissionLogVerifier/tree/main/uav-ledger

My contributions in this repo focus on:
- defense-relevant problem framing (mission assurance vs “crypto”)
- architecture + threat model documentation
- verification strategy, test plan, and results reporting
- restructuring the codebase into a maintainable, reviewable repo

---

## Status
Actively being refactored and documented for a professional engineering portfolio.
