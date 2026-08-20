# CMSC Exchange security package

This branch contains the complete CMSC Exchange API package from the source implementation, plus session authentication, in-memory rate limits, deterministic regression coverage, and CI smoke coverage.

## Covered

- CMSC quote API
- CMSC payment intent API
- session authentication (`401` when unauthenticated)
- quote and intent rate limits
- validation and deterministic quote calculations
- FastAPI TestClient dependency (`httpx`)
- backend compile smoke
