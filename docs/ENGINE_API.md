# Engine interfaces

This is an integration reference checked against the current working tree on 2026-11-19. Source remains authoritative where implementation changes. These interfaces have no explicit negotiated API version yet.

## Python facade

```python
from core import DoomEngine

engine = DoomEngine(download_dir="./downloads", max_workers=2)
try:
    formats = engine.get_formats()
    info = engine.resolve_url("https://example.com/video", expand_collection=False)
    item = engine.enqueue("https://example.com/file.zip", format_label="Original file")
    # Retain the engine while queued work runs. Call stop() when the host shuts down.
finally:
    engine.stop()
```

The example illustrates ownership and cleanup; it does not wait for the queued item to finish.

| Method | Current purpose |
| --- | --- |
| `is_ffmpeg_ready()`, `get_formats()` | Capabilities and available format profiles |
| `resolve_url(url, expand_collection=False)` | Inspect media and suggested mode |
| `download(url, format_label=..., progress_callback=..., cancel_event=...)` | Blocking download returning a file path |
| `enqueue(url, format_label=..., ...)` | Queue one item; returns a `DownloadItem` |
| `enqueue_batch(text_or_urls, format_label=None, ...)` | Parse links, optionally expand collections, enqueue items |
| `get_queue()`, `get_stats()` | Current items and aggregate state |
| `pause()`, `resume()` | Queue dispatch controls |
| `cancel(id)`, `retry(id)`, `remove(id)`, `clear_completed()` | Item/queue maintenance |
| `stop()` | Stop scheduling and request cancellation during host shutdown |

Use exact output labels from `get_formats()` for facade/HTTP calls. CLI shorthand is normalized by the CLI; do not assume every transport accepts the same aliases. Batch default selection also differs from the synchronous method's default.

## HTTP adapter

```powershell
python main.py --server --host 127.0.0.1 --port 8080
```

| Request | Behavior |
| --- | --- |
| `GET /api/status` | Engine status, FFmpeg availability, destination, stats |
| `GET /api/formats` | Output profiles |
| `GET /api/info?url=<encoded-url>&expand=true` | Media inspection and optional collection expansion |
| `GET /api/queue` | `{ "queue": [...], "stats": {...} }` snapshot |
| `POST /api/download` | Enqueue from JSON; returns `202` with `enqueued_count` and `item_ids` |
| `POST /api/queue/pause` | Pause dispatch |
| `POST /api/queue/resume` | Resume dispatch |
| `POST /api/queue/clear` | Clear finished items |
| `POST /api/queue/<id>/cancel` | Request cancellation |
| `POST /api/queue/<id>/retry` | Retry an item |

Download request example:

```json
{"url":"https://example.com/file.zip","format":"Original file","expand":false,"skip_existing":true}
```

`download_dir` is also accepted. Queue entries include `id`, `url`, `title`, `artist`, `duration`, `format_label`, `status`, `percent`, `speed_str`, `eta_str`, `status_message`, `error_message`, and `filepath`. Poll the queue for progress; this server does not implement WebSockets or SSE.

The server currently has no authentication, uses permissive CORS, and accepts destination paths. Use loopback for local integration. Public/remote serving needs a separate deployment and access-control design.

## CLI / JSON process adapter

```powershell
python main.py info "https://example.com/video" --json
python main.py formats --json
python main.py check --json
python main.py download "https://example.com/video" -q 1080p --json-progress
```

`--json-progress` emits newline-delimited JSON for process consumers. Read the process exit code and both output streams. Inspect `core/cli.py` when relying on event types or fields; do not parse human progress text as an API or assume every progress event has a percentage.

## Known contract gaps

- Per-item pause/resume exists on `QueueManager`, but is not exposed by the facade or HTTP routes listed above. Global queue pause is not the same action.
- HTTP status currently hardcodes `1.0.0`, while `VERSION` currently reads `1.2.0`. Do not use that field as a reliable compatibility negotiation mechanism yet.
- Queue items are mutable Python objects; HTTP builds a separate plain-data representation. Avoid exposing locks, events, or image objects to clients.
- Transport coverage and error handling differ. Schema versioning, consistent validation, and adapter parity remain future work.

When changing a contract, document the new behavior here, add relevant compatibility checks, identify affected consumers in the ledger, and avoid silently changing existing payload meanings.
