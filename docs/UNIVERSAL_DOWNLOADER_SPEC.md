# Project direction

## Goal

A reusable Python engine for supported media and direct downloads, usable by desktop apps, command-line tools, local services, and future clients. Keep the interface minimal and keep transfer behavior in one engine.

Read [the architecture](ARCHITECTURE.md) for current ownership, [the interface reference](ENGINE_API.md) for available adapters, and [the ledger](../LEDGER.md) for recent work.

## Existing working-tree implementation

The checkout contains media extraction and conversion, website inspection and fallback scraping, direct HTTP transfers, range segments and partial state, queue controls, a Python facade, CLI JSON output, a local HTTP server, and a CustomTkinter frontend. It also contains platform-specific detection such as Steam and Spotify matching. These mechanisms do not establish that every platform or URL works today.

Some of this work is uncommitted at the documentation handoff. `VERSION` and historical changelog entries are not substitutes for a release reference or a test run. Validate the exact revision before publishing capabilities or performance claims.

## Priorities for future work

1. Establish a versioned engine contract and consistent behavior across Python, CLI, HTTP, and queued execution.
2. Validate pause/resume, range-server fallback, cancellation, and state recovery with reproducible transfer tests.
3. Package the canonical engine independently and record how app distributions consume its version.
4. Add another frontend as an engine consumer, with download logic remaining in the core.
5. Evaluate bandwidth limits, connection tuning, authenticated requests, browser integration, and headless packaging as separate scoped features.

These are directions, not implemented promises. No replacement frontend, browser companion, WebSocket transport, or universal performance guarantee is established by this document.

## Completion evidence

A feature is ready when its implementation, affected adapters, relevant checks, known limits, and handoff entry are recorded. Measure performance before calling a change faster. Validate source availability before claiming website support. Keep partial state when it is required for resume rather than applying blanket temporary-file cleanup.
