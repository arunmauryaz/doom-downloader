# Agent instructions

## Before changing the project

1. Read [LEDGER.md](LEDGER.md) first: start with the latest entries, then read earlier entries relevant to your task.
2. Read [README.md](README.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
3. For engine or integration work, read [docs/ENGINE_API.md](docs/ENGINE_API.md) and inspect the actual implementation.
4. Run `git status --short` and inspect the relevant diff. Existing uncommitted work may belong to the user or another agent. Preserve it; do not reset, overwrite, stage, or publish it as your own.

The ledger is shared project memory. These files are the handoff context; do not assume another chat's private memory is available.

## Engine ownership

- `core/` is the engine source of truth in this repository. Prefer the `DoomEngine` facade for new consumers.
- Download behavior belongs in the engine, not in individual frontends. Keep GUI/framework imports out of `core/`.
- The existing GUI uses lower-level engine services too. Preserve its behavior until an explicit migration changes that wiring.
- Python calls, local HTTP/JSON, and CLI/NDJSON are different adapters to the same engine. Do not implement a separate downloader for a new UI.
- A standalone engine copy must be built or synchronized from a recorded engine revision. Do not independently patch duplicate copies. If a separate canonical engine repository is introduced, record its location and revision and update the ownership docs.
- Changes to public methods, formats, queue states, progress fields, or transport payloads need compatibility review, relevant tests, and an update to the interface documentation.
- Clearly label planned capabilities. Do not describe a frontend, API action, release, or passing test run as complete without evidence.

## Required ledger entry

Append an entry to `LEDGER.md` for every meaningful code, documentation, configuration, or release change before handing off. Include:

- Date and unique entry ID; agent/tool name or session identifier.
- Task, files changed, and the resulting behavior or decision.
- Engine/frontend/interface impact, including compatibility changes.
- Checks actually run and their outcomes; explicitly state what was not tested.
- Remaining work or known issues, and commit/release references if they exist.

Use the ledger's template. Never invent an author, timestamp, test result, commit, or release. Do not rewrite another agent's history. Correct an older entry with a new dated entry referencing it. For concurrent work, use distinct entry IDs, re-read before saving, and preserve other agents' additions.

## Finishing a task

Run checks appropriate to the change. Documentation-only work needs link and implementation-consistency checks, not a new runtime test claim. Review the diff, update the ledger, and report remaining limitations. Keep local settings, credentials, environments, downloaded media, and generated artifacts out of commits. Commit or publish only within the user's authorized scope.
