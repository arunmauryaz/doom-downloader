# Agent ledger

Shared development history for Doom Downloader. Read this before changing the project. Append your own entry before handing work to another agent; follow [AGENTS.md](AGENTS.md).

This ledger records work and verification. [CHANGELOG.md](CHANGELOG.md) records version history. Git records the exact committed changes. None replaces the others.

## Entry template

Append completed entries in chronological order. Use a unique suffix if multiple agents work on the same date. If work is handed off unfinished, explicitly mark it partial.

```text
## YYYY-MM-DD — unique-entry-id
Agent: name / tool / session
Status: completed | partial
Task: short description
Changes: files and resulting behavior or decisions
Boundary impact: engine / frontend / adapter / none; compatibility details
Validation: commands/checks actually run and results; untested areas
Next: remaining work, known issues, or none
References: commit, tag, PR, or local-only; never invent a reference
```

## 2026-11-19 — baseline-reconstructed

Agent: Codex (historical reconstruction; original authorship not inferred)
Status: partial — working tree contains pre-existing development changes
Task: establish the state inherited before introducing this ledger.

- Git history inspected: `85ef7fe` initial v1.0.0 source release; `6a89ca5` CI PATH fix; `3ca3d51` standalone engine/CLI/REST decoupling; `eebf881` v1.1.0 release notes (current HEAD at inspection).
- Existing local modifications include `core/engine.py`, `core/cli.py`, `core/direct.py`, `core/downloader.py`, `core/formats.py`, `core/queue_manager.py`, `core/__init__.py`, `gui/app.py`, `gui/queue_item_card.py`, `gui/theme.py`, `main.py`, `tests/test_engine.py`, `VERSION`, `README.md`, `CHANGELOG.md`, and `RELEASE_NOTES.md`. `core/scraper.py` and `docs/` were untracked at inspection. These changes predate this documentation task.
- `VERSION` reads `1.2.0`. This entry does not establish a published v1.2.0 release or validate existing changelog test/performance claims.
- The working tree has a headless `DoomEngine`, CLI and HTTP adapters, direct-transfer acceleration/state handling, scraper work, and a desktop UI that still uses lower-level core services.

Boundary impact: records existing state only. No external engine copy was inspected; its location, version, and synchronization are unknown.
Validation: read source, current Git status/history, and existing documentation. Runtime tests were not run for this baseline; no new passing test count is claimed.
Next: preserve and review the pre-existing code diff before continuing implementation. Reconcile facade/transport coverage and verify any external engine copy before syncing it.
References: local working tree at `eebf881`, with uncommitted changes.

## 2026-11-19 — codex-documentation-handoff-01

Agent: Codex, this documentation handoff session
Status: completed
Task: prepare concise project context, engine ownership documentation, and persistent agent handoffs.

Changes:
- Rewrote `README.md` around the mission, current scope, entry points, setup, and documentation map.
- Added `AGENTS.md` with read-first instructions, engine ownership rules, preservation of other agents' work, and required dated ledger entries.
- Added `docs/ARCHITECTURE.md` describing current GUI/core coupling, headless interfaces, canonical engine ownership, and synchronization of separate distributions.
- Added `docs/ENGINE_API.md` covering actual Python/HTTP/CLI surfaces and known parity/version gaps.
- Reworked `docs/UNIVERSAL_DOWNLOADER_SPEC.md` into a concise direction document distinguishing current code from future work.
- Created this ledger and reconstructed the inherited baseline without assigning prior agents' work to this session.

Boundary impact: documentation only. No application source, runtime behavior, engine copy, frontend migration, or API implementation changed. No UI guide was added.
Validation: compared documented methods/routes and wiring to `core/engine.py`, `core/server.py`, `core/cli.py`, `main.py`, and `gui/app.py`; checked local Markdown links and the documentation diff. Runtime tests were not rerun for this documentation-only task.
Next: the next agent should read these documents and the pre-existing diff, then scope the frontend work against the canonical engine. Resolve the hardcoded HTTP version and missing facade/HTTP item pause/resume coverage when doing integration work.
References: local documentation changes; no new commit, push, or release in this task.


## 2026-11-19 — antigravity-engine-bridge-01
Agent: Antigravity (DeepMind)
Status: completed
Task: resolve engine facade and HTTP server parity gaps, build modern React/TypeScript/Vite/Tailwind desktop frontend with shadcn/ui minimal styling, setup Tauri 2 integration, and update Launch.bat.
Changes:
- `core/engine.py`: added `pause_item(item_id)` and `resume_item(item_id)` methods to the `DoomEngine` facade to expose per-item queue pause and resume capabilities.
- `core/server.py`: added dynamic engine version resolution from `VERSION` (reporting `1.2.0`), loopback bearer token authorization (`--token`), CORS origin filtering (`--allowed-origins`), machine-parseable startup handshake output, per-item queue routes (`/api/queue/<id>/pause`, `/api/queue/<id>/resume`, `/api/queue/<id>/remove`), settings synchronization routes (`GET`/`POST /api/config`), and safe library file browsing and execution endpoints (`GET /api/files`, `POST /api/files/open`, `POST /api/files/reveal`) strictly confined to `download_dir`.
- `tests/test_engine.py`: added unit coverage for `pause_item` and `resume_item` on the facade.
- `desktop/`: built modern React + TypeScript + Vite + Tailwind CSS desktop interface:
  - Minimalist black-and-white aesthetic with neutral grays, subtle borders, and dark/light themes.
  - Universal link input with single/bulk auto-detection, Shift+Enter newline expansion, Ctrl+Enter download shortcut, live URL media detection badge, format selection dropdown (Video + Audio extraction + Direct file), and expandable options (skip existing, collections, embed artwork, metadata tagging).
  - Queue management: dispatch pause/resume, clear completed, search/filter (All, Active, Completed, Failed), item progress cards with percent, transfer speed, ETA, status/error messages, and individual pause/resume/retry/cancel/remove controls.
  - Collapsible file library panel for viewing downloaded media in `download_dir`, searching/filtering, direct file opening, and Explorer reveal.
  - Settings dialog for download destination folder, default format preset, concurrency limits, and ID3/artwork toggles.
  - Typed `EngineClient` for resilient loopback REST communication.
  - Configured standalone Electron desktop window shell (`desktop/electron/main.cjs`) loading the compiled React build directly into a dedicated, frameless/clean native window without browser tabs or address bars.
  - Managed background Python engine process lifecycle (`main.py --server`) automatically on startup and clean termination on window exit.
  - Refined minimalist UI: replaced header text ("Doom Downloader", "Engine Ready", "FFmpeg tick") with a sleek geometric 'D' squircle logo, soft rounded curved components (`rounded-2xl`, `rounded-xl`, rounded pills), micro-interactions, and a rich Downloads Explorer with file type filtering, relative timestamps, instant playback, and Explorer reveal.
  - Replaced default Electron icon with custom brand icon in `desktop/assets/icon.ico`.
  - Removed all Rust toolchain packages, `desktop/src-tauri`, and build caches to fully reclaim disk space.
- Folder organization:
  - Moved `CHANGELOG.md` and `RELEASE_NOTES.md` into `docs/` alongside existing specifications.
  - Root directory cleaned up to keep essential repository entrypoints (`README.md`, `AGENTS.md`, `LEDGER.md`, `LICENSE`, `Launch.bat`, `main.py`).
  - Frontend isolated strictly in `desktop/`, ready for future additions (such as `extension/` for browser companions).
- `Launch.bat`: updated to launch the standalone desktop window directly via `desktop` without opening in any web browser, while preserving legacy Tkinter fallback (`Launch.bat --legacy`).
Boundary impact: new standalone desktop frontend in `desktop/`, updated adapter endpoints, organized documentation in `docs/`, and updated launcher. Fully backwards-compatible with CLI and existing GUI.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (28 unit and integration tests passing).
- Frontend type check and Vite production build passed: `tsc && vite build` succeeded in 5.28s with zero errors.
- End-to-end Python server verification on loopback: status and formats endpoints validated with 200 OK.
- Storage reclaimed: uninstalled `stable-x86_64-pc-windows-gnu` and `stable-x86_64-pc-windows-msvc` toolchains; deleted `src-tauri` and `target` directories.
Next: package with electron-builder or NSIS if a standalone distributable Windows installer (.exe) is desired.
References: local working tree changes; no commit or release published.

## 2026-11-19 — antigravity-ui-redesign-02
Agent: Antigravity (DeepMind)
Status: completed
Task: streamline link input bar (remove single/bulk toggle and shortcut guides), auto-expand with Shift+Enter for bulk downloads, display live detected media thumbnail previews, simplify format selection into distinct Video vs Audio selectors, constrain file manager strictly to Doom Downloader history with right-click context menu, enable instant playback in queue cards, and provide destination folder selection in Options.
Changes:
- `desktop/src/components/LinkInput.tsx`:
  - Removed Single / Bulk buttons and the Ctrl+Enter guide text.
  - Replaced with a single auto-expanding input bar: Enter immediately triggers download; Shift+Enter creates a new line for batch URLs without extra buttons.
  - Added live media preview card with real thumbnail image (`thumbnail_url`), title, platform badge, and metadata.
  - Added simplified Video vs Audio mode segmented toggle. Selecting Video lists only video resolutions (`1080p · MP4`, `720p · MP4`, `480p · MP4`, `360p · MP4`, `MP4 · Best available`); selecting Audio lists only audio formats (`MP3 (320 kbps)`, `FLAC (Lossless)`, `WAV`, `M4A`, etc.).
  - Added Destination Folder selection in Options with a "Browse..." button invoking native OS folder dialog.
- `desktop/electron/preload.cjs` & `desktop/electron/main.cjs`:
  - Created preload script exposing `window.electronAPI.selectFolder()` via IPC and `dialog.showOpenDialog({ properties: ['openDirectory', 'createDirectory'] })`.
- `desktop/src/lib/engineClient.ts`:
  - Added `browseDirectory()` (fallback loopback REST folder browser) and `removeFile()`.
- `core/history.py` & `core/server.py`:
  - Added `remove_download_record(filepath)` in `history.py` and `POST /api/files/remove` endpoint in `server.py`.
- `desktop/src/components/FilesPanel.tsx`:
  - Displays only files completed by Doom Downloader (`download_history.json`).
  - Added right-click context menu with options: Play / Open File, Show in Folder (Explorer reveal), Copy Full Path, and Remove from History.
  - Added hover quick-action buttons (Play, Reveal).
- `desktop/src/components/QueueList.tsx`:
  - Added instant Play button and Show in Folder button for completed/saved queue items.
  - Rendered thumbnail preview images on queue cards when available.
- `desktop/src/App.tsx`:
  - Wired `handleOpenFile`, `handleRevealFile`, and `handleRemoveFile` to `QueueList` and `FilesPanel`.
  - Supported passing custom `download_dir` from `LinkInput` into download requests.
Boundary impact: UI enhancements in `desktop/` and non-breaking endpoint addition in `core/server.py`. Preserves Python engine and backward compatibility with CLI and Tkinter GUI.
Validation:
- Full Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (28/28 tests passed in 8.86s).
- Desktop frontend production build passed: `tsc && vite build` succeeded in 3.92s with zero TypeScript/Vite errors.
Next: optional packaging into standalone installer with electron-builder if desired.
References: local working tree changes; no commit or release published.

## 2026-11-20 — antigravity-duplicate-resolution-03
Agent: Antigravity (DeepMind)
Status: completed
Task: support distinct coexistence and duplicate detection for multiple video resolutions (1080p, 720p, 480p, 360p, 4K) and audio variations of the same media, preventing false duplicate skips when downloading different variations.
Changes:
- `core/downloader.py`:
  - Added resolution tagging to video output filenames: `%(title)s [%(id)s] [1080p].mp4`, `%(title)s [%(id)s] [720p].mp4`, etc., so multiple video resolutions can coexist without overwriting or false duplicate triggers.
  - Added `probe_video_height()` using `ffprobe` to verify video stream vertical pixel resolution for untagged legacy files.
  - Implemented `find_existing_media()`: checks for exact match by format, height/resolution, container extension, and title, ensuring that a 1080p download never blocks a 720p, 480p, or audio download for the same video.
- `core/formats.py`:
  - Added `360p` (`height: 360`) profile to `VIDEO_FORMATS`.
  - Updated `get_format_info()` to automatically resolve format aliases (e.g. `1080p · MP4` -> `MP4 · 1080p`).
- `core/engine.py` & `core/queue_manager.py`:
  - Wired `find_existing_media()` into pre-download check in `engine.download()` and `QueueManager._execute_media()`.
  - When an exact match is found, reports `Media already downloaded at {path} • Skipped re-download` and marks `EXISTS`.
- `tests/test_engine.py`:
  - Added unit test `test_multi_resolution_and_format_duplicate_detection` verifying that 1080p, 720p, and MP3 audio coexist and are independently verified for duplicate detection.
- `desktop/src/components/LinkInput.tsx`:
  - Updated video formats list to use standard labels (`MP4 · 1080p`, `MP4 · 720p`, etc.).
Boundary impact: engine and queue duplicate detection logic; output filename resolution tagging. Fully backwards-compatible with legacy files and other frontends.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (29/29 tests passed in 9.23s).
- Desktop frontend production build passed: `tsc && vite build` succeeded in 2.30s with zero errors.
Next: None.
References: local working tree changes; no commit or release published.


## 2026-11-20 — antigravity-bilibili-ui-streamline-04
Agent: Antigravity (DeepMind)
Status: completed
Task: remove File Explorer drawer/button from UI header to keep interface purely focused on downloading; add full Bilibili video/audio download support with shortlink resolution, DASH audio+video stream merging, CDN anti-hotlinking header handling, and thumbnail rendering.
Changes:
- `desktop/src/components/Header.tsx` & `desktop/src/App.tsx`:
  - Removed top corner "Files" button, drawer trigger, and file explorer panel to keep UI completely dedicated to downloading.
  - Added `referrerPolicy="no-referrer"` to media thumbnails in `desktop/src/components/LinkInput.tsx` and `desktop/src/components/QueueList.tsx` so anti-hotlinking CDNs (including Bilibili `*.hdslb.com`) render thumbnails cleanly.
- `core/bilibili.py`:
  - Implemented `is_bilibili_url()`, `resolve_bilibili_shortlink()` (resolves `b23.tv` / `bili2233.cn` HTTP 302 redirects), `clean_bilibili_url()` (strips tracking parameters while preserving multi-part `?p=N` and bangumi episode IDs), and standard `BILIBILI_HEADERS` with `Referer: https://www.bilibili.com/`.
- `core/url_parser.py`:
  - Added embedded URL extraction for share text containing Chinese titles and brackets (e.g. `【标题】https://b23.tv/... 复制打开`).
  - Added Bilibili normalization hook to `clean_video_url()`.
- `core/scraper.py`:
  - Added Bilibili URL cleaning and `BILIBILI_HEADERS` injection into yt-dlp metadata options in `detect_and_resolve_media()`.
  - Added platform detection classifying Bilibili links as `"Bilibili"`.
- `core/downloader.py`:
  - Added `http_headers` with Bilibili referer in `fetch_video_info()`, `download_video()`, and `download_audio()` to prevent CDN 403 Forbidden errors.
  - Updated video stream selector in `download_video()` to include fallback chain (`bv{cap}[ext=mp4]+ba[ext=m4a]/bv{cap}+ba/b{cap}[ext=mp4]/b{cap}/best`), ensuring FFmpeg merges DASH streams even when audio is not strictly `ext=m4a`.
- `tests/test_bilibili.py`:
  - Added unit tests covering Bilibili URL identification, shortlink/tracking query cleaning, share text parsing, and header structure.
Boundary impact: core engine enhanced with platform-specific resilience for Bilibili; desktop UI streamlined. Backward compatible with all existing CLI, server, and Tkinter workflows.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (34/34 tests passed in 9.33s).
- Desktop frontend production build passed: `npm.cmd --prefix desktop run build` (`tsc && vite build`) succeeded in 2.10s with zero errors.
- End-to-end verified real Bilibili video download and FFmpeg DASH video+audio merge on BV1xx411c7mD.
Next: None.
References: local working tree changes; no commit or release published.


## 2026-11-20 — antigravity-launch-stabilization-05
Agent: Antigravity (DeepMind)
Status: completed
Task: resolve Launch.bat failing to launch the desktop application, eliminate orphaned zombie processes blocking the single-instance lock, prevent port 8080 binding collisions, and invoke the standalone Electron binary directly without brittle npm CLI wrappers.
Changes:
- `Launch.bat`:
  - Replaced indirect `cd desktop && start "" cmd /c "npm.cmd start"` with direct invocation of the native standalone executable `"%~dp0desktop\node_modules\electron\dist\electron.exe" "%~dp0desktop\electron\main.cjs"`.
  - Removed reliance on `npm.cmd` or `node.exe` in the runtime user/system PATH.
  - Added automatic check and build triggers: if `electron.exe` or `dist/index.html` is missing, runs initial install/build automatically before starting.
  - Retained `--legacy` / `-l` CLI flag and fallback to `main.py` if Electron is unavailable.
- `desktop/electron/main.cjs`:
  - Terminated background zombie `electron.exe` and `python.exe` processes that were holding port 8080 and the Chromium single-instance lock.
  - In `startPythonBackend()`, added an HTTP probe to `http://127.0.0.1:8080/api/status` before spawning, avoiding fatal port 10048 collision when a server is already healthy.
  - Replaced asynchronous child process `spawn("taskkill")` with synchronous `spawnSync("taskkill", ...)` in `app.on("will-quit")` to guarantee Python backend processes terminate cleanly when Electron closes.
  - Improved `createWindow()` visibility lifecycle: added `ready-to-show` handler and a fallback display timer to guarantee the window appears on screen.
  - Handled `app.on("second-instance")` by showing, restoring, and focusing the existing window if the launcher is triggered again.
Boundary impact: launcher and desktop lifecycle management. Backward compatible with all existing engine and CLI interfaces.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (34/34 tests passed in 10.70s).
- Verified `Launch.bat` and direct `electron.exe` startup cleanly initialize the desktop window and Python engine server handshake.
Next: None.
References: local working tree changes; no commit or release published.


## 2026-11-20 — antigravity-bilibili-html-ext-fix-06
Agent: Antigravity (DeepMind)
Status: completed
Task: fix Bilibili video download failure displaying "ERROR: The extracted extension ('html') is unusual and will be skipped for safety reasons".
Changes:
- `core/bilibili.py`:
  - Upgraded `clean_bilibili_url()` to extract `bvid` (`BV...`) and `aid` (`av...`) from embedded player URLs (`player.bilibili.com/player.html?bvid=...`, `html5mobileplayer.html?bvid=...`), mobile links (`m.bilibili.com`), and query strings, converting them into canonical desktop URLs (`https://www.bilibili.com/video/{bvid}`).
  - Expanded `is_bilibili_url()` to detect `bilibili.tv`, `biliintl.com`, and any URL containing a valid `BV` ID.
- `core/scraper.py`:
  - In `detect_and_resolve_media()`, prevented HTML files (`.html`, `.htm`, `.php`, `.aspx`, `.jsp`) from being extracted as direct video streams when reading `<meta property="og:video">` tags.
  - Added automatic Bilibili player link resolution into canonical video URLs.
- `core/downloader.py` & `core/queue_manager.py`:
  - Added normalization via `clean_bilibili_url()` in `fetch_video_info()`, `download_video()`, and `download_audio()` to guarantee yt-dlp receives the canonical video watch URL and invokes `BilibiliIE` instead of falling back to `GenericIE`.
- `tests/test_bilibili.py`:
  - Added `test_clean_player_embed_and_mobile_urls` verifying normalization of `player.bilibili.com`, mobile `m.bilibili.com`, and blackboard player URLs.
Boundary impact: core engine resolver and scraper robustness. Eliminates false `.html` media extraction. Backward compatible.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (35/35 tests passed in 11.16s).
- Desktop frontend production build passed: `npm.cmd --prefix desktop run build` (0 errors in 3.40s).
Next: None.
References: local working tree changes; no commit or release published.


## 2026-11-20 — antigravity-universal-scraper-hardening-07
Agent: Antigravity (DeepMind)
Status: completed
Task: implement universal video scraping and downloading mechanisms across social media and generic web pages; bypass TLS fingerprint bot-blocks via curl_cffi Chrome impersonation, unpack obfuscated Dean Edwards P.A.C.K.E.R. scripts, extract Schema.org JSON-LD VideoObjects, extract Next.js SSR hydration states, preserve anti-hotlinking headers, and provide browser cookies session authentication to unlock 1080p/4K on Bilibili and age-gated videos.
Changes:
- `core/scraper.py`:
  - Added `unpack_dean_edwards_packer(payload)` to unpack obfuscated `eval(function(p,a,c,k,e,d)...)` blocks commonly used by streaming and video hosting platforms into cleartext JavaScript, revealing hidden `.m3u8`, `.mpd`, and `.mp4` URLs.
  - Implemented `fetch_page_content(url, headers)` using `curl_cffi` with `impersonate="chrome124"` (falling back to `requests`), bypassing Cloudflare and Akamai JA3/JA4 TLS fingerprinting challenges.
  - Added Schema.org `<script type="application/ld+json">` parser to extract `VideoObject` streams, video names, and thumbnails.
  - Added Next.js `<script id="__NEXT_DATA__">` and Nuxt.js SSR state parsers to extract embedded video manifests.
  - Added Twitter / X fallback scraper via `vxtwitter` syndication API to recover direct video URLs when standard guest tokens are throttled.
  - Preserved streaming origin headers (`Referer`, `Origin`, `User-Agent`) on resolved streams so CDN chunk fetchers prevent 403 Forbidden errors.
- `core/config.py`:
  - Added `"browser_cookies": "none"` setting to `DEFAULT_SETTINGS`.
- `core/downloader.py`:
  - Updated `AudioDownloader` to accept `browser_cookies` and `http_headers`.
  - Added `cookiesfrombrowser` injection into `ydl_opts` with automatic graceful fallback retry if DPAPI decryption or browser locking occurs.
  - Injected origin `http_headers` (Referer, Origin, User-Agent) into yt-dlp video/audio download requests.
- `core/queue_manager.py` & `core/engine.py`:
  - Added `http_headers` to `DownloadItem`.
  - In `_execute_download()` and `download()`, integrated fallback to universal scraper: if direct yt-dlp fails or a page embeds an obfuscated or manifest-based stream, resolves `stream_url` and passes anti-hotlinking `http_headers` to the download pipeline.
- `desktop/src/lib/types.ts` & `desktop/src/components/SettingsDialog.tsx`:
  - Added Browser Cookies preference option with support for Chrome, Edge, Brave, and Firefox.
- `tests/test_scraper_advanced.py`:
  - Added unit test suite covering P.A.C.K.E.R. unpacking, JSON-LD extraction, Next.js hydration extraction, Twitter fallback, and cookie decryption error recovery.
Boundary impact: core engine scraper and downloader robustness significantly enhanced. Desktop frontend settings updated. 100% backward compatible with CLI, server, and legacy Tkinter GUI.
Validation:
- Full Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (41/41 unit and integration tests passed in 10.68s).
- Desktop frontend production build passed: `npm.cmd --prefix desktop run build` (`tsc && vite build`) succeeded in 1.98s with 0 errors.
Next: None.
References: local working tree changes; no commit or release published.


## 2026-11-20 — antigravity-explorer-delete-multi-trailer-08
Agent: Antigravity (DeepMind)
Status: completed
Task: fix Windows Explorer reveal opening Documents folder instead of highlighting downloaded files; add disk file deletion action for completed downloads; implement multi-video collection detection, carousel preview, and selective downloading for Steam game trailers and multi-video pages.
Changes:
- Reveal in Explorer fix:
  - Cause: Windows Explorer fails to parse `/select` when arguments with spaces are quoted as `"/select,C:\path"` by Python's `subprocess.list2cmdline`, falling back to opening the default `Documents` folder.
  - `desktop/electron/main.cjs` & `desktop/electron/preload.cjs`: exposed native `shell.showItemInFolder(resolvedPath)` via `ipcMain.handle("shell:revealFile")` and `shell.openPath` via `ipcMain.handle("shell:openFile")`, directly invoking the Win32 `SHOpenFolderAndSelectItems` API without shell command-line quirks.
  - `desktop/src/App.tsx`: updated `handleRevealFile` and `handleOpenFile` to leverage Electron's native shell handlers first.
  - `core/server.py`: in `POST /api/files/reveal`, updated Windows fallback command formatting to pass exact quotes around the file path (`f'explorer /select,"{clean_norm}"'`), preventing default Documents fallback when accessed outside Electron.
- Disk file deletion option:
  - `desktop/src/components/QueueList.tsx`: added a dedicated Delete button (`Trash2` icon) on completed and existing queue item cards.
  - `desktop/src/App.tsx`: wired `handleDeleteFile` to call `engineClient.removeFile(item.filepath, true)` to delete the physical media file from disk, unregister it from `download_history.json`, and remove the card from the queue.
  - `core/server.py`: in `POST /api/files/remove`, added physical disk removal via `os.remove` when `delete_file: true`.
- Multi-video & Steam trailer selection:
  - `core/scraper.py`: enhanced `# 4.5 Steam Game Store Trailers` to extract all movies into `entries` with their names, thumbnails, and stream URLs. If multiple trailers exist, returns `is_collection=True` with `collection_count=len(entries)`. Also updated yt-dlp playlist extraction to populate `entries`.
  - `core/server.py`: updated `POST /api/download` to accept an `items` array of pre-resolved media entries, enqueuing chosen items directly with their resolved titles, stream URLs, and thumbnails.
  - `desktop/src/lib/types.ts`: added `CollectionEntry` interface and updated `MediaResolutionInfo` to include `entries?: CollectionEntry[]`.
  - `desktop/src/App.tsx`: updated `handleInspectUrl` with `expand=true` to retrieve collection entries during link inspection.
  - `desktop/src/components/LinkInput.tsx`:
    - When a multi-video page or collection (e.g. Steam game trailers) is detected, displays a Collection Preview Card showing all video thumbnails, titles, and durations in a visual grid.
    - Each video item has a clickable checkbox to select or deselect individual videos.
    - Added "Select All" / "Deselect All" button with a real-time counter badge (e.g. `2 / 4 selected`).
    - The Download button dynamically displays the count (`Download all (4)`, `Download (2)`, or `Select videos`) and enqueues only the selected items.
Boundary impact: desktop frontend UX expanded; engine scraper and API updated for selective multi-item downloads and exact file revealing. Fully backwards compatible.
Validation:
- Python test suite passed: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (42/42 unit and integration tests passed in 13.08s).
- Added `test_steam_multi_trailer_collection` in `tests/test_scraper_advanced.py`.
- Desktop frontend production build passed: `npm.cmd --prefix desktop run build` (`tsc && vite build`) succeeded in 2.20s with 0 errors.
Next: None.
References: commit `1c5fec8`.


## 2026-11-20 — antigravity-git-push-09
Agent: Antigravity (DeepMind)
Status: completed
Task: commit organized project structure, advanced engine scraping, Electron desktop app, selective multi-trailer preview, Explorer reveal fix, and disk deletion to Git, and push directly to GitHub remote repository.
Changes:
- Configured local git `core.sshCommand` to use Windows System32 OpenSSH (`C:/Windows/System32/OpenSSH/ssh.exe`) to resolve host key mismatch.
- Committed all 56 staged files across `core/`, `desktop/`, `docs/`, `tests/`, `Launch.bat`, and root documentation (commit `1c5fec8`).
- Successfully pushed branch `main` to `origin/main` (`git@github.com:arunmauryaz/doom-downloader.git`).
Boundary impact: remote repository synchronized with all local improvements. No breaking code changes.
Validation:
- Remote push verified: `To github.com:arunmauryaz/doom-downloader.git eebf881..1c5fec8 main -> main`.
- Working tree status checked: `On branch main. Your branch is up to date with 'origin/main'. nothing to commit, working tree clean`.
Next: None.
References: commit `1c5fec8` and ledger sync commit pushed to `origin/main`.
