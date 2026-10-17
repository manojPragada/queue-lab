# Queue Lab

Explore a durable SQLite queue with idempotency keys, retries and dead-letter states.

**Status:** runnable CLI foundation. No hosted demo or dashboard is available yet. Examples use synthetic offline data. Python 3.10+; standard library only. Validated with Python 3.12.

## Quick start

```bash
git clone https://github.com/manojPragada/queue-lab.git
cd queue-lab
python --version
python app.py --db demo.sqlite3 enqueue welcome '{"message":"hello"}'
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 enqueue failure '{"demo_fail":true}' --max-attempts 2
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 work
python app.py --db demo.sqlite3 list
```

Use `python3` if your system does not provide `python`. No package installation or API key is needed.

## Usage and behavior

Each `work` command processes at most one pending job. Payloads with `demo_fail: true` fail deliberately; after the retry limit they enter `dead`. Other payloads complete without executing external work. Reusing an idempotency key returns the same job ID; differing payload or retry configuration is rejected.

Run `python app.py --help` for available options.

## Development and verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py tests
```

Tests exercise behavior with temporary/local data. PufferFish's recording test uses only a loopback HTTP server. There is no build step or configured linter; compilation is a syntax check, not linting.

## Configuration

Configuration is provided through CLI arguments. No environment variables, `.env` file, credentials or external services are required. `.env.example` documents this intentionally empty configuration contract.

## Structure

```text
app.py          CLI and core domain functions
tests/          behavioral unit tests
ROADMAP.md      completed work and prioritized next steps
.env.example    configuration notes
```

Queue examples are the self-contained commands above.

## Architecture

A single dependency-free module exposes importable core functions and a CLI entry point. Filesystem and network access occur only when the corresponding commands run. This small foundation will be split into a package, integrations and UI as those features arrive; see the roadmap.

## Limitations

This is a transactional demonstration handler, not a production distributed queue. There are no leases, delayed backoff, custom handlers or dashboard yet. Do not perform network side effects inside the transaction. SQLite database files stay local and are ignored by git.

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
