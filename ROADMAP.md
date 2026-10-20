# Roadmap

## Completed

- [x] Runnable standard-library CLI foundation
- [x] Behavioral tests and documented local examples
- [x] Input handling, explicit limitations and setup guide

## Next

- [x] Add scheduled retries, backoff and dead-letter replay
- [x] Add queue snapshots and transactional job lifecycle events
- [ ] Add safe handler registration, worker heartbeats and leases
- [ ] Build queue dashboard with explicit state transitions

## Continuity

2026-10-20: Added an explicit allowlist of bounded local handlers, persisted results/error codes, result CLI and additive database migration. Six tests cover execution, retries, replay clearing, invalid handlers and JSON numbers. Next: worker leases/heartbeats before allowing external or long-running handlers. No dashboard or distributed-worker guarantees yet.

Initial foundation implemented and checked on 2026-10-17. Inspect current code and commits before continuing. Prioritize the first unchecked item and keep improvements small enough to verify. No visual dashboard has been implemented.


2026-10-18: Added persisted retry deadlines, bounded exponential backoff, dead-job replay and legacy SQLite migration. Nine tests pass with controlled timestamps and no sleeps. Next: handler boundaries and lifecycle metrics.


2026-10-19: Added stats/events CLI commands, ready/delayed counts and durable lifecycle records retained across replay. Legacy jobs have no fabricated history. Next: explicit handler and worker lifecycle boundaries before the dashboard.

