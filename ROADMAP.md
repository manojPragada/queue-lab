# Roadmap

## Completed

- [x] Runnable standard-library CLI foundation
- [x] Behavioral tests and documented local examples
- [x] Input handling, explicit limitations and setup guide

## Next

- [x] Add scheduled retries, backoff and dead-letter replay
- [ ] Add safe handler registration and worker lifecycle metrics
- [ ] Build queue dashboard with explicit state transitions

## Continuity

Initial foundation implemented and checked on 2026-10-17. Inspect current code and commits before continuing. Prioritize the first unchecked item and keep improvements small enough to verify. No visual dashboard has been implemented.


2026-10-18: Added persisted retry deadlines, bounded exponential backoff, dead-job replay and legacy SQLite migration. Nine tests pass with controlled timestamps and no sleeps. Next: handler boundaries and lifecycle metrics.
