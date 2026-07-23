# Smooth song-progress display for polling clients

This document describes how a client of the SqueezeWatch HTTP API should display
song elapsed time so that it ticks smoothly at one second per second, with no
visible skips or backward jumps, even though the underlying data arrives by
polling. It is self-contained: it covers the API contract, the algorithm, and
the rationale, so it can be implemented in any language (the web client in
`static/player.js` is the reference implementation).

## API contract

`GET /api/zone/{zone_id}/status` returns JSON including:

| Field | Type | Meaning |
|---|---|---|
| `position_sec` | float or null | Song position in seconds as last sampled from the audio source |
| `position_age_sec` | float or null | Seconds elapsed (server wall clock) since that sample was taken |
| `duration_sec` | float or null | Song duration in seconds; null when unknown (e.g. radio streams) |
| `mode` | string | `play`, `pause`, `stop`, or `unknown` |

Key facts about the data:

- The server does not sample continuously. For LMS sources it subscribes to
  status pushes every **5 seconds** (plus extra off-cycle updates after seeks,
  pause/play, and track changes). Consecutive client polls therefore usually
  return the **same** `position_sec` with a growing `position_age_sec`.
- `position_sec` itself carries source-side error: the value LMS reports can be
  stale or quantized by up to a second or two relative to the audio actually
  playing. Two successive samples are not guaranteed to be mutually consistent
  to better than roughly ±1–2 seconds.
- `position_age_sec` only measures time since the server *received* the sample.
  While the player is paused or stopped, the age keeps growing but the true
  position does not move.

Consequence: a client that displays `position_sec + position_age_sec` directly
on every poll will jitter forward and backward by a few seconds, worst just
after each 5-second source push. That is the bug this algorithm fixes.

## Algorithm

The client maintains a **local playback clock** and treats the server values as
periodic, noisy corrections to it — snap only on real discontinuities, slew
otherwise.

### State

- `base` (seconds, or unset) — position at the moment `baseTime` was recorded
- `baseTime` — local monotonic clock reading when `base` was set
- `playing` — true when `mode == "play"`
- `lastDuration`, `lastMode` — previous poll's values, for change detection
- `lastDisplayedSecond` (integer, or unset) — monotonic display guard

### Rendering (run at 4 Hz or faster)

```
local = base
if playing:
    local += now() - baseTime          # seconds
clamp local to [0, duration]
displayedSecond = floor(local)
if playing and lastDisplayedSecond is set and displayedSecond < lastDisplayedSecond:
    displayedSecond = lastDisplayedSecond      # monotonic guard
lastDisplayedSecond = displayedSecond
render displayedSecond (and local/duration for the progress bar)
```

### On each status poll (e.g. every 1 second)

```
# 1. Server's estimate of the position right now.
serverPosition = position_sec
if mode == "play":
    serverPosition += position_age_sec       # do NOT add age when paused/stopped

# 2. Client's current estimate (same formula as rendering, unclamped).
local = base + (playing ? now() - baseTime : 0)     # unset if base unset

# 3. Snap on a real discontinuity:
snap if any of:
    - local is unset (first poll, or position was unavailable)
    - duration_sec != lastDuration          (track changed)
    - mode != lastMode                      (play/pause/stop transition)
    - |serverPosition - local| > SNAP_THRESHOLD

snap means:  base = serverPosition; baseTime = now(); clear lastDisplayedSecond

# 4. Otherwise slew — absorb the error gradually:
    base = local + (serverPosition - local) * SLEW_GAIN
    baseTime = now()
```

If `position_sec` or `duration_sec` is null, clear all progress state and hide
the progress display.

### Optimistic local actions

When the user seeks, or presses previous/next track, **snap immediately** to
the target position (0 for prev/next) before sending the request, so the UI
responds instantly. These are snaps: clear the monotonic guard.

### Tuning constants

- `SNAP_THRESHOLD = 2.0` seconds. Larger than the worst normal sampling noise
  (~1–2 s), smaller than any deliberate seek a user would notice. Errors above
  it mean a real discontinuity happened (seek from another client, track jump)
  and the display should move at once rather than crawl.
- `SLEW_GAIN = 0.1` per poll. With 1-second polls, each correction moves the
  clock by at most `0.1 × 2 s = 0.2 s` — invisible in an `m:ss` display — while
  persistent drift converges with a ~10-poll (10-second) time constant, well
  within one song.

## Why each rule exists

- **Local clock, not server values, drives the display.** The display advances
  from the local monotonic clock, so it ticks perfectly at 1 s/s regardless of
  polling jitter, network latency, or the 5-second source cadence.
- **Age is only added while playing.** During pause the sample stays fixed but
  its age grows; adding age would make the position drift forward while paused
  and then jump on the next correction.
- **Slew instead of snap for small errors.** Small errors are sampling noise,
  not truth; snapping to them is what caused the visible 1:42 → 1:46 → 1:45
  jitter. Slewing keeps long-term accuracy (the clock is always pulled toward
  the server) without short-term ugliness.
- **Monotonic whole-second guard.** The display shows `floor(seconds)`, so even
  a 0.05-second negative slew correction can cross a second boundary and tick
  the clock backwards. Holding the displayed second until the real value
  catches up (at most a fraction of a second later, since slew corrections are
  tiny) hides that. The guard must reset on every snap, otherwise a legitimate
  backward seek would freeze the display.
- **Mode change forces a snap.** On pause→play the age semantics change, and on
  track transitions mode often flickers; snapping re-anchors cleanly. Duration
  change likewise catches track changes even when positions happen to be close.

## Implementation notes for C++

- Use a monotonic clock (`std::chrono::steady_clock`) for `baseTime`, never
  wall time.
- Represent "unset" state explicitly (`std::optional`), not with sentinel
  values like -1.
- The render tick and the poll handler touch the same state; if they run on
  different threads, guard the state with a mutex (the reference JS client is
  single-threaded so it does not need one).
