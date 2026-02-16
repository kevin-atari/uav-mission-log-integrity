# Project Contributions and Roles

This document clarifies individual contributions for the UAV Mission Log Integrity System.
The project originated as a collaborative academic effort and has been reframed here as a professional engineering portfolio artifact.

---

## Kevin Atari — Blockchain & Backend Integration Lead

Primary responsibilities:
- Implemented the **blockchain backend integration** for mission log integrity
- Integrated with the Ethereum Sepolia testnet using `web3.py`
- Worked with the FlightLogRegistry smart contract logic
- Implemented secure SHA-256 hashing of UAV flight logs
- Designed and implemented backend endpoints for:
  - mission (flight) registration
  - checkpoint / version anchoring
- Managed Ethereum transaction lifecycle:
  - RPC connectivity
  - private key signing
  - nonce handling
  - transaction submission and receipt tracking
- Enabled the end-to-end pipeline:
  log generation → hash computation → on-chain anchoring → verification

These components form the **trust backbone** of the system.

---

## Team Contributions (Baseline)

- **Jacob Wald** — Verification logic and frontend tooling (baseline reference)
- **Erika Valle-Baird** — Log simulation and storage integration (baseline reference)

This repository represents independent restructuring, documentation, and extension of the original team work with emphasis on mission assurance and backend system design.
