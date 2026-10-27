# Roadmap

## Completed

- [x] Runnable standard-library CLI foundation
- [x] Behavioral tests and documented local examples
- [x] Input handling, explicit limitations and setup guide

## Next

- [x] Add scheduled retries, backoff and dead-letter replay
- [x] Add queue snapshots and transactional job lifecycle events
- [x] Add safe handler registration, worker heartbeats and leases
- [x] Build read-only queue dashboard with explicit state transitions
- [x] Add token-gated dead-letter replay control with confirmation
- [x] Add coordinated pause/resume controls for new claims
- [x] Add graceful drain status for active leases

## Continuity

2026-10-27: Added read-only active-lease summaries grouped by worker ID, with next/last expiry and no payload exposure. Next: explicit worker registration only if durable multi-process identity becomes a goal.

2026-10-26: Added a read-only drain status reporting pause state, active unexpired leases, the latest lease deadline and whether the queue is fully drained. Available through CLI and dashboard snapshot API; it never cancels work. Next: explicit worker registration only if multi-process coordination becomes a goal.

2026-10-25: Added durable queue pause/resume state, CLI commands and an ephemeral-token-gated dashboard control. Pausing atomically blocks new claims but never interrupts leased work. Next: explicit graceful-drain status for active leases.

2026-10-24: Added one deliberately narrow mutation: confirmed dead-letter replay gated by an ephemeral session token printed only to the local terminal. Payloads remain hidden; the token is not stored by the page. Next: coordinated worker pause/drain controls with explicit ownership semantics.

2026-10-22: Added a polished loopback-only dashboard for bounded job summaries, queue metrics and the latest lifecycle transitions. Payloads/results are never exposed and the interface is read-only. Next: carefully scoped local controls with confirmation and CSRF protection.

2026-10-21: Added durable worker ownership, bounded leases, heartbeats and deterministic recovery of expired claims. The built-in worker now executes outside the claim transaction and finalizes only while it owns the job. Delivery remains at-least-once. Next: expose these state transitions in the local dashboard.

2026-10-20: Added an explicit allowlist of bounded local handlers, persisted results/error codes, result CLI and additive database migration. Six tests cover execution, retries, replay clearing, invalid handlers and JSON numbers. Next: worker leases/heartbeats before allowing external or long-running handlers. No dashboard or distributed-worker guarantees yet.

Initial foundation implemented and checked on 2026-10-17. Inspect current code and commits before continuing. Prioritize the first unchecked item and keep improvements small enough to verify. No visual dashboard has been implemented.


2026-10-18: Added persisted retry deadlines, bounded exponential backoff, dead-job replay and legacy SQLite migration. Nine tests pass with controlled timestamps and no sleeps. Next: handler boundaries and lifecycle metrics.


2026-10-19: Added stats/events CLI commands, ready/delayed counts and durable lifecycle records retained across replay. Legacy jobs have no fabricated history. Next: explicit handler and worker lifecycle boundaries before the dashboard.

