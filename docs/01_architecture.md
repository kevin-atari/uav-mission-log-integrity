# UAV Mission Log Integrity System — Architecture

This document defines the architecture of the UAV Mission Log Integrity System, with emphasis on the **blockchain backend and verification pipeline**.

---

## High-level architecture

UAV / Simulator
|
v
Flight Logs (Files)
|
v
Hashing & Normalization
|
v
Backend API (Python)
|
+--> AWS S3 (log storage)
|
+--> Ethereum Smart Contract (hash anchoring)


---

## Core components

### 1. Flight log input
- Raw UAV telemetry logs
- Multiple versions / checkpoints supported
- Treated as untrusted after mission completion

---

### 2. Hashing & integrity layer (security-critical)

**Functions**
- Compute SHA-256 hashes of log files
- Ensure deterministic hashing (same input → same hash)
- Produce hash values used both on-chain and during verification

**Purpose**
This layer cryptographically binds off-chain data to on-chain records.

---

### 3. Backend API (Python)

This is the **primary integration layer** and the main contribution focus.

#### Responsibilities
- expose programmatic endpoints
- manage blockchain interactions
- handle transaction lifecycle
- coordinate off-chain and on-chain state

---

### 4. Blockchain integration (Ethereum)

**Network**
- Ethereum Sepolia testnet

**Contract**
- FlightLogRegistry (or equivalent)

**Functions**
- register new UAV missions
- store initial log hash
- append checkpoint hashes
- expose immutable audit history

---

## Critical backend endpoints

### Endpoint 1 — Flight Registration

**Purpose**
- Initialize a new mission on-chain

**Behavior**
- accept mission metadata
- compute or accept initial log hash
- submit Ethereum transaction
- return transaction hash and confirmation data

This establishes the **root of trust** for a mission.

---

### Endpoint 2 — Checkpoint Anchoring

**Purpose**
- Append new integrity checkpoints over time

**Behavior**
- accept updated log hash
- link checkpoint to existing mission
- preserve chronological ordering
- submit transaction and return receipt

This enables **time-ordered, tamper-evident mission histories**.

---

## Ethereum client layer (Python)

**Responsibilities**
- RPC connectivity
- private key signing
- nonce management
- transaction submission
- receipt polling and confirmation handling

This layer ensures backend endpoints are **robust and programmatically usable**, not just demos.

---

## Verification pipeline

1. retrieve stored log
2. recompute SHA-256 hash
3. fetch on-chain hash history
4. compare expected vs actual
5. report PASS / FAIL
6. identify first divergence point (if any)

---

## Architectural strengths

- clear separation of concerns
- blockchain used only where immutability is required
- backend-first design
- reproducible verification
- extensible to non-blockchain ledgers if needed

---

## Explicit non-claims

- no real-time guarantees
- no prevention of tampering
- no identity or access control assumptions
- no operational deployment claims
