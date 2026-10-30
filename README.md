# Queue Lab

Explore a durable SQLite queue with idempotency keys, retries and dead-letter states.

**Status:** runnable CLI and local dashboard with one token-gated dead-letter action. No hosted demo is available. Examples use synthetic offline data. Python 3.10+; standard library only. Validated with Python 3.12.

## Quick start

```bash
git clone https://github.com/manojPragada/queue-lab.git
cd queue-lab
python --version
python app.py --db demo.sqlite3 enqueue welcome '{"message":"hello"}'
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 enqueue failure '{"demo_fail":true}' --max-attempts 2 --retry-delay 0
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 list
```

Use `python3` if your system does not provide `python`. No package installation or API key is needed.

## Usage and behavior

The dashboard renders the same payload-free active worker lease summary as `worker-leases`, including lease counts, server-computed seconds remaining, and local next-expiry times; no worker control or registration is implied.

`python app.py --db queue.sqlite3 worker-leases` groups active unexpired leases by worker ID with counts and expiry bounds. It exposes no payloads, results, or errors and does not control workers.

Each `work` command processes at most one pending job. Payloads with `demo_fail: true` fail deliberately; after the retry limit they enter `dead`. Other payloads complete without executing external work. Reusing an idempotency key returns the same job ID; differing payload or retry configuration is rejected.

Run `python app.py --help` for available options.

Use `python app.py --db queue.sqlite3 pause` to atomically stop new claims and `resume` to allow them again. Already leased jobs are not interrupted. The same action is available in the loopback dashboard only with the ephemeral session token and an explicit browser confirmation; this is cooperative local coordination, not process supervision or cancellation.

After pausing, `python app.py --db queue.sqlite3 drain-status` reports active unexpired leases, their latest deadline and whether the queue is drained. Expired leases no longer count as active. This is observation only: it does not wait, signal workers or cancel jobs.

## Local queue dashboard

```bash
python app.py --db demo.sqlite3 dashboard --port 8765
```

Open http://127.0.0.1:8765. The responsive dashboard shows queue-state totals, up to 100 recent jobs and 50 recent lifecycle transitions. It binds only to IPv4 loopback, makes no external requests and never exposes job payloads or results. The process prints an ephemeral session token: paste it into the page only when you need to replay a dead job, then confirm the specific job. The token is kept only in page memory, and all other mutations remain CLI-only. Loopback binding and a bearer token are development safeguards, not production authentication. Stop with Ctrl+C.

## Scheduled retries and replay

`enqueue --retry-delay SECONDS` sets the initial delay (default 1 second, range 0–3600). A failed attempt becomes eligible after `min(3600, retry_delay × 2^(attempt-1))` seconds. The exponent is bounded at 12 for numerical safety. `work` processes only currently eligible jobs and returns null when none are due; it does not sleep or run a worker loop. `available_at` is a Unix timestamp; a value of 0 means immediately eligible or terminal. Keep invoking work from your own worker loop when needed.

The quick-start failure example uses zero delay so both attempts can be demonstrated immediately. For a dead job, run `python app.py --db demo.sqlite3 replay JOB_ID`. Replay preserves the job ID, payload, key and retry policy, resets attempts, and makes the job eligible now. Non-dead or nonexistent jobs cannot be replayed. Listing includes retry policy and next eligibility time. Existing databases migrate automatically with an immediate eligibility timestamp and a one-second default retry delay.

## Queue snapshots and job history

```bash
python app.py --db demo.sqlite3 stats
python app.py --db demo.sqlite3 events --limit 20
python app.py --db demo.sqlite3 events --job-id 1
```

Stats distinguish ready and delayed pending jobs, current terminal states, current attempt counters, and recorded failures/events. Event rows are appended transactionally with enqueue, retry, completion, dead-letter and replay changes. They contain IDs, kinds, attempt numbers and Unix timestamps, never payloads. Replaying resets a job's current attempts but retains recorded failure history. `events` is newest-first by event ID, with a 1–1000 row limit.

Existing jobs are not given invented past events during migration: recorded counts cover activity after this feature was installed. There is no retention pruning, worker heartbeat or distributed-worker monitoring yet. Event history can grow over time. Programmatic tests may inject `now`; real CLI operations use the system clock.

## Worker leases and crash recovery

Each built-in `work` call claims one ready job as `running` under a 30-second `local-worker` lease, executes the allowlisted handler outside the claim transaction, then finalizes only while it still owns the claim. The importable `claim_job`, `heartbeat`, and `finish_job` functions support explicit worker identities and 1–3600 second leases. An expired claim is recovered by the next worker, recorded as `lease_expired`, and counts as another attempt.

This provides bounded crash recovery, not exactly-once execution: a handler may finish its side effect just before a worker disappears, then run again after lease expiry. Handlers must remain idempotent. This version has no continuously running worker process; the dashboard observes state but does not run workers.

## Development and verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py dashboard.py handlers.py tests
```

Tests exercise temporary SQLite databases, clock-controlled retry eligibility and legacy database migration without sleeping. There is no build step or configured linter; compilation is a syntax check, not linting.

## Configuration

Configuration is provided through CLI arguments. No environment variables, `.env` file, credentials or external services are required. `.env.example` documents this intentionally empty configuration contract.

## Structure

```text
app.py          CLI and core domain functions
handlers.py     fixed allowlist of bounded local demo handlers
dashboard.py    loopback dashboard server and bounded snapshot
dashboard/      dependency-free browser interface
tests/          behavioral unit tests
ROADMAP.md      completed work and prioritized next steps
.env.example    configuration notes
```

Queue examples are the self-contained commands above.

## Architecture

### Allowlisted demo handlers and persisted results

```bash
python app.py --db demo.sqlite3 enqueue greeting '{"handler":"uppercase","text":"Hello town"}'
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 result 1
```

Use a new demo database for the example ID. The fixed registry in `handlers.py` permits only `noop` (default for legacy payloads) and `uppercase` (a string of at most 10,000 characters). Payloads never select imports, shell commands or executable code. Unknown handlers and invalid text use normal retry/dead-letter transitions with stable error codes. Results and last errors persist in SQLite; replay clears them without erasing event history. New columns migrate existing databases without inventing results for old completed jobs. Non-finite JSON numbers are refused on enqueue. Outputs can contain your supplied text: keep databases private.

These bounded demo handlers execute within the existing single-worker SQLite transaction. This is not arbitrary plugin registration, external-job execution, worker leasing or crash recovery. Do not put network calls or long-running work inside this transaction; leases/heartbeats remain next.

The dependency-free CLI in app.py owns SQLite state, retry scheduling, events and result inspection. handlers.py defines the fixed local handler allowlist. There are no network calls or provider integrations. A package and UI remain future work; see the roadmap.

## Limitations

This is an at-least-once demonstration queue, not a production distributed system. There is no worker process supervisor; the only dashboard mutation is confirmed, token-gated dead-letter replay. SQLite database files stay local and are ignored by git.

## Running and deployment

Run locally from the repository using the commands above. No hosted deployment has been configured. Do not expose a development process publicly. A web deployment guide will be added when a web application actually exists.

## Troubleshooting

- **Python not found:** install Python 3.10+ or try `python3`.
- **File not found:** run from the repository root or provide an absolute input path.
- **Invalid input:** inspect the error printed to standard error and compare with the examples.
- **Permission denied:** choose a folder you own; avoid running as administrator.

## Contributing and credits

Open an issue describing the observed behavior, expected result and a minimal synthetic example. Keep changes focused, include behavioral tests, run the checks above, and update this README when commands or capabilities change. Do not submit credentials or private input files.

Implementation and synthetic examples are original to this repository. There are no third-party runtime dependencies or media assets. A redistribution license has not yet been selected; public visibility alone does not grant an open-source license.



