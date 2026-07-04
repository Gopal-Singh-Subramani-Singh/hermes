# Architecture Decision Records

This directory documents key architectural decisions made during the design of Hermes.
Each ADR captures the context, options considered, and rationale for a specific decision.

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-router-strategy.md) | Pluggable Routing Strategy with Per-Request Override | Accepted |
| [ADR-002](ADR-002-circuit-breaker.md) | Per-Backend Circuit Breaker with Sliding Window | Accepted |
| [ADR-003](ADR-003-redis-over-kafka.md) | Redis for Queueing and Rate Limiting over Kafka | Accepted |
| [ADR-004](ADR-004-sse-over-websocket.md) | Server-Sent Events over WebSocket for Streaming | Accepted |
| [ADR-005](ADR-005-fastapi-over-go.md) | FastAPI (Python) over Go for Gateway Implementation | Accepted |

## Format

Each ADR follows this structure:

- **Status** — Accepted / Superseded / Deprecated
- **Context** — What problem are we solving and why does it need a decision?
- **Decision** — What we chose and how it works
- **Alternatives Considered** — What else was evaluated and why it was rejected
- **Consequences** — Pros and cons of the chosen approach
- **Outcome** — Where in the codebase this decision lives and how it is tested

## Adding a new ADR

1. Copy an existing ADR as a template
2. Number sequentially (`ADR-006-...`)
3. Add a row to the table above
4. Link from `HERMES_TECHNICAL_REPORT.md` if it affects a documented section
