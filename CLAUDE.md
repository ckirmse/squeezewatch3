# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SqueezeWatch3 bridges a NuVo multi-zone audio amplifier with a Logitech Media Server (LMS/Squeezebox) music library. It handles serial communication with the NuVo hardware, TCP communication with LMS, and exposes a small HTTP web interface for zone control.

## Running

```bash
python squeezewatch.py
```

The app connects to the NuVo amplifier on `/dev/ttyS0` at 57600 baud and to LMS on host `mario` port 9090. The HTTP interface listens on port 8000.

## Building Templates

Jinja2 templates in `templates/` are used directly — no compilation step needed. The `.html` files are rendered at request time. Each page has a corresponding `*Logic.py` class (e.g. `homeLogic.py`) that provides the template context via `get_context()`.

## Architecture

The application is **event-driven** using Python's native `asyncio` framework, structured around three protocol handlers that communicate through a central app object.

### Core Data Flow

```
NuVo hardware (serial) <-> NuVoProtocol <-> SqueezeWatchApp <-> SqueezeCLIProtocol/Factory <-> LMS (TCP)
                                                   |
                                         FastAPI/uvicorn HTTP server
```

### Key Components

**`SqueezeWatchApp.py`** — Central singleton (`app` global). Holds all application state: player list, source→player mapping, and caches for artists/albums/tracks/playlists/favorites. All playback control methods live here (`play`, `pause`, `nextTrack`, etc.). Data-fetch methods (`getArtists`, `getFavorites`, etc.) are `async def` — they return cached data immediately or `await` an LMS query.

**`NuVoProtocol.py`** — Serial `asyncio.Protocol` for the NuVo amplifier. Handles zone on/off events, source selection, button presses, and sends menu/display data back to zones. Idle timer logic auto-shuts zones after inactivity (300s for app-controlled, 10800s for externally-controlled). Writes go through an internal `asyncio.Queue` drained by a background coroutine with 2ms delays between sends.

**`NuVoZone.py`** — State machine per zone. Tracks which menu the user is browsing (main, artists, albums, tracks, playlists, favorites, settings) and dispatches button presses. Menu state IDs 27–33 are hardcoded for different browsing levels. LMS data fetches are fire-and-forget `asyncio.create_task` calls to `_fetch_*` coroutines.

**`SqueezeCLIProtocol.py` / `SqueezeCLIFactory.py`** — TCP `asyncio.Protocol` connecting to LMS port 9090. Sends URL-encoded CLI commands, parses key-value responses. Uses a `context_map` dict of `asyncio.Future` objects keyed by a sequence number to match async responses to their callers. Factory `getXxx` methods are `async def` — they create a Future, register it, send the command, and `await` the result.

**`RequestHTML.py` / `renderTemplate.py`** — FastAPI/uvicorn HTTP stack. `RequestHTML` parses action parameters and dispatches to Jinja2 templates; logic classes in `templates/` (e.g. `homeLogic.py`) extend `RequestLogic` and provide `get_context()` for template rendering.

**`Log.py`** — Logging utility. Use `log()`, `elog()` (errors), `dlog()` (debug). Writes to `log.txt`, `error.txt`, `debug.txt` with timestamps and caller function names.

### Important Implementation Details

- **NuVo encoding:** ISO-8859-1 (not UTF-8). Special characters must be escaped via `zigutils.nuvoEscapeString()`.
- **LMS responses:** URL-encoded key-value pairs. Parsed in `SqueezeCLIProtocol`.
- **Source→player mapping** is fragile by design (see comment in `SqueezeWatchApp.py`) — multiple zones sharing a source can conflict.
- **Button press timing:** Presses under 500ms trigger prev/next track; longer presses trigger fast-forward/rewind.
- **Async LMS queries:** `SqueezeCLIFactory` get* methods are `async def` that create an `asyncio.Future`, send the LMS command with a context tag, and `await` the Future. `SqueezeCLIProtocol.dispatchResult` resolves the Future when the response arrives. Callers `await` the factory method or spawn it as a `create_task`.
- **`asyncio.TimerHandle`** (returned by `call_later`) has `.cancel()` but no `.reset()`. NuVoZone uses a `_reset_idle_timer(delay)` helper that cancels and reschedules.

### Reference

`NUVO Protocol.pdf` in the repo root is the authoritative NuVo serial protocol specification.
