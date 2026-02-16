# Security Practices

This repository follows standard security hygiene practices.

## Secrets management
- Secrets (API keys, private keys, credentials) must **never** be committed.
- Runtime configuration is provided via environment variables.
- `.env.example` documents required variables without values.

## Blockchain keys
- Ethereum private keys used for testing should be disposable.
- Testnet credentials must be rotated if exposed.
- No mainnet keys are used or required.

## Scope
All content in this repository is unclassified and suitable for public release.
