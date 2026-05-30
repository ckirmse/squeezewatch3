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

Cheetah templates must be compiled before use:

```bash
cd templates && make
```

`.tmpl` files compile to `.py` files. Run this after modifying any `.tmpl` file.

## Architecture

The application is **event-driven** using the Twisted framework, structured around three protocol handlers that communicate through a central app object.

### Core Data Flow

```
NuVo hardware (serial) <-> NuVoProtocol <-> SqueezeWatchApp <-> SqueezeCLIProtocol/Factory <-> LMS (TCP)
                                                   |
                                              HTTP server
```

### Key Components

**`SqueezeWatchApp.py`** — Central singleton (`app` global). Holds all application state: player list, source→player mapping, and caches for artists/albums/tracks/playlists/favorites. All playback control methods live here (`play`, `pause`, `nextTrack`, etc.).

**`NuVoProtocol.py`** — Serial `LineReceiver` for the NuVo amplifier. Handles zone on/off events, source selection, button presses, and sends menu/display data back to zones. Idle timer logic auto-shuts zones after inactivity (300s for app-controlled, 10800s for externally-controlled).

**`NuVoZone.py`** — State machine per zone. Tracks which menu the user is browsing (main, artists, albums, tracks, playlists, favorites, settings) and dispatches button presses. Menu state IDs 27–33 are hardcoded for different browsing levels.

**`SqueezeCLIProtocol.py` / `SqueezeCLIFactory.py`** — TCP `LineReceiver` connecting to LMS port 9090. Sends URL-encoded CLI commands, parses key-value responses. Uses a context/callback dict to match async responses to their requests.

**`RequestRoot.py` / `RequestHTML.py` / `renderTemplate.py`** — Twisted Web HTTP stack. `RequestHTML` parses action parameters and dispatches to Cheetah templates; logic classes in `templates/` (e.g. `homeLogic.py`) extend `RequestLogic` and provide `renderHTMLPage()`.

**`Log.py`** — Logging utility. Use `log()`, `elog()` (errors), `dlog()` (debug). Writes to `log.txt`, `error.txt`, `debug.txt` with timestamps and caller function names.

### Important Implementation Details

- **NuVo encoding:** ISO-8859-1 (not UTF-8). Special characters must be escaped via `zigutils.nuvoEscapeString()`.
- **LMS responses:** URL-encoded key-value pairs. Parsed in `SqueezeCLIProtocol`.
- **Source→player mapping** is fragile by design (see comment in `SqueezeWatchApp.py`) — multiple zones sharing a source can conflict.
- **Button press timing:** Presses under 500ms trigger prev/next track; longer presses trigger fast-forward/rewind.
- **Deferred pattern:** Async LMS queries use Twisted `Deferred` objects with a context dict keyed by command string to route responses back to the right callback.

### Reference

`NUVO Protocol.pdf` in the repo root is the authoritative NuVo serial protocol specification.
