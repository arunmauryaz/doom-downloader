# Architecture and engine ownership

## Principle

One Python engine, multiple consumers. The engine owns media detection, extraction, direct transfers, conversion, metadata, queue state, and transfer recovery. Frontends own presentation, input interactions, and platform-specific file dialogs or file opening.

“Separate” means independent responsibilities and a headless backend. “Connected” means a frontend calls an engine interface and renders its results. It does not mean that each frontend has its own download implementation.

## Current structure

```text
main.py
  |-- GUI mode --> gui/ --> core services and QueueManager
  |-- CLI mode --> core/cli.py --> DoomEngine
  `-- HTTP mode --> core/server.py --> DoomEngine
                                      |
                                      +-- detection / scraping / URL parsing
                                      +-- downloaders / FFmpeg / tagging
                                      `-- queue / progress / configuration
```

| Component | Responsibility |
| --- | --- |
| `core/engine.py` | `DoomEngine`: public facade for inspection, downloads, queue access, and lifecycle |
| `core/scraper.py`, `url_parser.py`, `spotify.py` | Link classification, media discovery, collections, Spotify metadata matching |
| `core/downloader.py` | yt-dlp media download and FFmpeg processing |
| `core/direct.py` | HTTP file transfers, range segments, and partial state |
| `core/queue_manager.py` | Concurrent scheduling, item state, progress callbacks, cancellation/retry and item pause/resume methods |
| `core/formats.py`, `tagger.py` | Output profiles, aliases, metadata, and artwork |
| `core/config.py` | Current shared settings and download-directory defaults |
| `core/cli.py`, `server.py` | Process/JSON and HTTP adapters |
| `gui/` | Current CustomTkinter frontend |

## Current coupling to account for

`main.py` constructs `DoomEngine` but gives the GUI `engine.downloader` and `engine.queue_manager`. The GUI also imports configuration, formats, URL parsing, and scraper functions directly. It receives queue callbacks and marshals updates onto its GUI event loop. It does **not** currently control all engine behavior through HTTP.

The CLI and HTTP server use `DoomEngine`. The facade's synchronous download path and the queue's execution path are separate orchestration paths; changing one is not evidence that the other changed. Check both when modifying transfer behavior.

Core modules do not import CustomTkinter, but the repository's requirements include desktop packages. The engine is not yet a separately packaged distribution with its own dependency manifest. Configuration is a module-level singleton and can create a default directory on import. Queue items may carry Pillow artwork objects; these are not suitable as JSON payloads. `get_queue()` returns live item objects, not immutable transport snapshots.

These are present integration constraints, not reasons to copy the engine into a frontend.

## Reusing the engine

- In a Python host, import `DoomEngine` and manage its lifecycle; call `stop()` on shutdown.
- In another process, use the existing local HTTP API or CLI JSON output. Serialize plain data at the boundary.
- Keep download logic, format validation, state transitions, and recovery in `core/`. A client should request actions and display state.
- Introduce a client adapter when needed so frontend components do not depend on Python internals or transport-specific payload details.
- Document compatibility changes and update every affected consumer. Do not assume HTTP, CLI, and GUI expose identical actions today.

## Standalone engine copies

The canonical engine inspected for this handoff is `core/` in this checkout. No external engine copy or separate engine repository was inspected. If one exists elsewhere, its synchronization status is unknown.

A separate engine distribution should carry a version, source repository, and exact commit reference. Engine fixes go into the canonical source first; consumers then update to that engine version. A bundled copy is a distribution artifact, not an independent source of truth. Before moving ownership to another repository, record the new canonical location here and in the ledger, and document how this app consumes it.

## Next boundary work

Future work can package the core independently, define versioned serializable contracts, reduce direct GUI access to internals, and align facade/HTTP/CLI queue controls. Any new frontend is a consumer of that work. No replacement UI implementation or framework migration is part of this documentation change.
