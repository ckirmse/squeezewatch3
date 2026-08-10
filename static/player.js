// Amplr player client logic.
// Expects globals from the template: bootstrapZones (array), initialZoneId (int or null).

let activeZoneId = initialZoneId;
const zonesById = {};
let activeStatus = null;
let sources = [];
let favorites = null;

const favoritesOverlay = document.getElementById('favorites-overlay');

let draggingVolume = false;
let lastVolumeSendTime = 0;

// Connection state, mirroring the ESP32 controller: a single failed status poll
// flips the UI into the trouble state, and the next successful poll clears it.
// serverErrorStatus is the HTTP status when the server answered with an error,
// and null when the server could not be reached at all.
let statusValid = false;
let serverContactFailed = false;
let serverErrorStatus = null;
let serverRetryCount = 0;

let progressBase = null;
let progressBaseTime = null;
let progressDuration = null;
let progressPlaying = false;
let progressLastDisplayedSecond = null;
let progressLastMode = null;

// Reconciliation tuning: differences larger than the snap threshold are treated
// as real discontinuities (seek, track change); smaller ones are slewed away
// gradually so the displayed clock never visibly skips or jumps back.
const PROGRESS_SNAP_THRESHOLD_SECONDS = 2;
const PROGRESS_SLEW_GAIN = 0.1;

// Near an expected song end, poll the server quickly so the next track's info
// shows immediately instead of waiting out the normal poll interval.
const POLL_INTERVAL_MS = 1000;
const FAST_POLL_INTERVAL_MS = 300;
// Slightly outlasts the server's own 8s fast-poll cap toward the WiiM.
const FAST_POLL_MAXIMUM_MS = 9000;
const TRACK_END_ANTICIPATION_SECONDS = 0.3;

let activeZonePollTimer = null;
let fastPollDeadline = null;
let lastTrackKey = null;
let trackEndPollSent = false;

bootstrapZones.forEach(function(zone) {
  zonesById[zone.id] = zone;
});

function clampFraction(value) {
  return Math.max(0, Math.min(1, value));
}

function formatTime(seconds) {
  seconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes + ':' + (remainder < 10 ? '0' : '') + remainder;
}

function sendAction(zoneId, action, extraQuery) {
  if (!statusValid) {
    return Promise.resolve(null);
  }
  let url = '/api/zone/' + zoneId + '/action?action=' + action;
  if (extraQuery) {
    url += '&' + extraQuery;
  }
  return fetch(url).catch(function() {
    return null;
  });
}

// ===== connection state =====

function setControlsDisabled(disabled) {
  document.getElementById('play-button').disabled = disabled;
  document.getElementById('prev-button').disabled = disabled;
  document.getElementById('next-button').disabled = disabled;
  document.getElementById('favorites-button').disabled = disabled;
  const volumeScrubberElement = document.getElementById('volume-scrubber');
  if (disabled) {
    volumeScrubberElement.classList.add('disabled');
  } else {
    volumeScrubberElement.classList.remove('disabled');
  }
}

function connectionStatusTitle() {
  if (serverErrorStatus !== null) {
    return 'Server error ' + serverErrorStatus;
  }
  if (serverContactFailed) {
    return 'Server unreachable';
  }
  return 'Connecting to server…';
}

function renderConnectionState() {
  const page = document.querySelector('.page');
  if (statusValid) {
    page.classList.remove('disconnected');
    return;
  }

  page.classList.add('disconnected');
  document.getElementById('connection-status-title').textContent = connectionStatusTitle();
  let detail = '';
  if (serverRetryCount > 0) {
    detail = 'retry ' + serverRetryCount;
  }
  document.getElementById('connection-status-detail').textContent = detail;

  setControlsDisabled(true);
  favoritesOverlay.classList.remove('open');
  // Refetch on recovery; the cached list may be stale by then.
  favorites = null;
}

function noteServerFailure(httpStatus) {
  statusValid = false;
  serverContactFailed = true;
  serverErrorStatus = httpStatus;
  ++serverRetryCount;
  renderConnectionState();
}

function noteServerSuccess() {
  if (!statusValid && sources.length === 0) {
    // The one-shot source load happens at page load and may have been the
    // request that failed; pick it back up now that the server is answering.
    loadSources();
  }
  statusValid = true;
  serverContactFailed = false;
  serverErrorStatus = null;
  serverRetryCount = 0;
  renderConnectionState();
}

// ===== now playing / progress =====

function currentLocalPosition() {
  if (progressBase === null) {
    return null;
  }
  let elapsed = progressBase;
  if (progressPlaying) {
    elapsed += (Date.now() - progressBaseTime) / 1000;
  }
  return elapsed;
}

function snapProgress(seconds) {
  progressBase = seconds;
  progressBaseTime = Date.now();
  progressLastDisplayedSecond = null;
}

function renderProgress() {
  if (!statusValid) {
    // Freeze the clock rather than keep counting off a position we can no
    // longer confirm with the server.
    return;
  }
  const seekBlock = document.getElementById('seek-block');
  if (progressBase === null || progressDuration === null) {
    seekBlock.classList.add('hidden');
    return;
  }
  let elapsed = currentLocalPosition();
  if (elapsed < 0) {
    elapsed = 0;
  }
  if (elapsed > progressDuration) {
    elapsed = progressDuration;
  }
  let displayedSecond = Math.floor(elapsed);
  if (progressPlaying && progressLastDisplayedSecond !== null && displayedSecond < progressLastDisplayedSecond) {
    displayedSecond = progressLastDisplayedSecond;
  }
  progressLastDisplayedSecond = displayedSecond;
  if (progressPlaying && !trackEndPollSent && currentLocalPosition() >= progressDuration) {
    // The song should have just ended; poll right away rather than waiting for
    // the next scheduled poll to notice.
    trackEndPollSent = true;
    pollActiveZone();
  }
  const percent = clampFraction(elapsed / progressDuration) * 100;
  seekBlock.classList.remove('hidden');
  document.getElementById('seek-fill').style.width = percent + '%';
  document.getElementById('seek-knob').style.left = percent + '%';
  document.getElementById('seek-elapsed').textContent = formatTime(displayedSecond);
  document.getElementById('seek-total').textContent = formatTime(progressDuration);
}

setInterval(renderProgress, 250);

function renderStatus(data) {
  activeStatus = data;

  const nowPlayingContent = document.getElementById('now-playing-content');
  if (data.is_on) {
    nowPlayingContent.classList.remove('hidden');
  } else {
    nowPlayingContent.classList.add('hidden');
  }

  setControlsDisabled(!data.is_on);

  let title = data.title;
  if (!title) {
    title = data.lines[3];
  }
  let artist = data.artist;
  if (!artist) {
    artist = data.lines[2];
  }
  let station = data.album;
  if (!station) {
    station = data.lines[1];
  }
  if (!title) {
    title = '—';
  }
  document.getElementById('track-title').textContent = title;
  document.getElementById('track-artist').textContent = artist || ' ';
  document.getElementById('station-name').textContent = station;

  const playButton = document.getElementById('play-button');
  playButton.className = 'round-button play-button mode-' + data.mode;

  const artBezel = document.getElementById('art-bezel');
  if (data.mode === 'play') {
    artBezel.classList.add('playing');
  } else {
    artBezel.classList.remove('playing');
  }

  const artworkImage = document.getElementById('artwork-image');
  if (data.artwork_url) {
    if (artworkImage.getAttribute('src') !== data.artwork_url) {
      artworkImage.src = data.artwork_url;
    }
  } else {
    artworkImage.removeAttribute('src');
    artworkImage.classList.remove('visible');
  }

  const previousDuration = progressDuration;
  const previousMode = progressLastMode;
  const localPosition = currentLocalPosition();

  progressPlaying = (data.mode === 'play');
  progressDuration = data.duration_sec;
  progressLastMode = data.mode;

  if (data.position_sec !== null && data.position_sec !== undefined && data.duration_sec) {
    // The server position sample only advances while playing; when paused or
    // stopped its age grows but the true position does not.
    let serverPosition = data.position_sec;
    if (data.mode === 'play') {
      serverPosition += (data.position_age_sec || 0);
    }
    let mustSnap = false;
    if (localPosition === null) {
      mustSnap = true;
    } else if (data.duration_sec !== previousDuration) {
      mustSnap = true;
    } else if (data.mode !== previousMode) {
      mustSnap = true;
    } else if (Math.abs(serverPosition - localPosition) > PROGRESS_SNAP_THRESHOLD_SECONDS) {
      mustSnap = true;
    }
    if (mustSnap) {
      snapProgress(serverPosition);
    } else {
      progressBase = localPosition + (serverPosition - localPosition) * PROGRESS_SLEW_GAIN;
      progressBaseTime = Date.now();
    }
  } else {
    progressBase = null;
    progressBaseTime = null;
    progressLastDisplayedSecond = null;
  }
  renderProgress();

  if (!draggingVolume) {
    renderVolume(data.volume);
  }

  document.getElementById('room-dropdown-name').textContent = data.zone_name;
  const dropdownDot = document.getElementById('room-dropdown-dot');
  if (data.is_on) {
    dropdownDot.classList.remove('off');
  } else {
    dropdownDot.classList.add('off');
  }

  if (zonesById[data.zone_id]) {
    zonesById[data.zone_id].is_on = data.is_on;
    zonesById[data.zone_id].source = data.source;
    zonesById[data.zone_id].volume = data.volume;
  }

  renderSourceChips();
  renderZoneChips();
}

const artworkImageElement = document.getElementById('artwork-image');
artworkImageElement.onload = function() {
  artworkImageElement.classList.add('visible');
};
artworkImageElement.onerror = function() {
  artworkImageElement.classList.remove('visible');
};

function scheduleNextActiveZonePoll(delayMilliseconds) {
  if (activeZonePollTimer !== null) {
    clearTimeout(activeZonePollTimer);
  }
  activeZonePollTimer = setTimeout(pollActiveZone, delayMilliseconds);
}

function computeNextPollDelay(data) {
  const trackKey = data.title + ' ' + data.duration_sec;
  const trackChanged = (lastTrackKey !== null && trackKey !== lastTrackKey);
  lastTrackKey = trackKey;
  if (trackChanged) {
    trackEndPollSent = false;
  }

  const localPosition = currentLocalPosition();

  if (fastPollDeadline !== null) {
    let positionWrapped = false;
    if (localPosition !== null && progressDuration !== null &&
        localPosition < progressDuration - PROGRESS_SNAP_THRESHOLD_SECONDS) {
      positionWrapped = true;
    }
    if (trackChanged || positionWrapped || progressDuration === null || Date.now() >= fastPollDeadline) {
      fastPollDeadline = null;
    } else {
      return FAST_POLL_INTERVAL_MS;
    }
  }

  if (progressPlaying && progressDuration !== null && localPosition !== null &&
      localPosition >= progressDuration - TRACK_END_ANTICIPATION_SECONDS) {
    fastPollDeadline = Date.now() + FAST_POLL_MAXIMUM_MS;
    return FAST_POLL_INTERVAL_MS;
  }
  return POLL_INTERVAL_MS;
}

function pollActiveZone() {
  if (activeZoneId === null) {
    scheduleNextActiveZonePoll(POLL_INTERVAL_MS);
    return;
  }
  fetch('/api/zone/' + activeZoneId + '/status')
    .then(function(response) {
      if (!response.ok) {
        throw response.status;
      }
      return response.json();
    })
    .then(function(data) {
      noteServerSuccess();
      let delayMilliseconds = POLL_INTERVAL_MS;
      if (data.zone_id === activeZoneId) {
        renderStatus(data);
        delayMilliseconds = computeNextPollDelay(data);
      }
      scheduleNextActiveZonePoll(delayMilliseconds);
    })
    .catch(function(failure) {
      if (typeof failure === 'number') {
        noteServerFailure(failure);
      } else {
        noteServerFailure(null);
      }
      scheduleNextActiveZonePoll(POLL_INTERVAL_MS);
    });
}

// The active-zone poll owns the connection state; this one only suppresses its
// own render so a failure does not blow up mid-update.
function pollAllZones() {
  fetch('/api/zones')
    .then(function(response) {
      if (!response.ok) {
        throw response.status;
      }
      return response.json();
    })
    .then(function(data) {
      data.zones.forEach(function(zone) {
        zonesById[zone.id] = zone;
      });
      renderZoneChips();
      renderRoomMenu();
    })
    .catch(function() {
    });
}

// ===== transport =====

document.getElementById('play-button').onclick = function() {
  sendAction(activeZoneId, 'play_pause').then(pollActiveZone);
};
document.getElementById('prev-button').onclick = function() {
  snapProgress(0);
  renderProgress();
  sendAction(activeZoneId, 'prev_track');
};
document.getElementById('next-button').onclick = function() {
  snapProgress(0);
  renderProgress();
  sendAction(activeZoneId, 'next_track');
};

// ===== scrubbers =====

function scrubberFraction(scrubber, clientX) {
  const rect = scrubber.querySelector('.scrubber-track').getBoundingClientRect();
  return clampFraction((clientX - rect.left) / rect.width);
}

const seekScrubber = document.getElementById('seek-scrubber');
seekScrubber.addEventListener('pointerdown', function(event) {
  if (!progressDuration || !statusValid) {
    return;
  }
  const fraction = scrubberFraction(seekScrubber, event.clientX);
  const seconds = Math.round(fraction * progressDuration);
  snapProgress(seconds);
  renderProgress();
  fetch('/api/zone/' + activeZoneId + '/seek?seconds=' + seconds).catch(function() {
  });
});

function renderVolume(percent) {
  if (percent === null || percent === undefined) {
    document.getElementById('volume-fill').style.width = '0%';
    document.getElementById('volume-knob').style.left = '0%';
    document.getElementById('volume-readout').textContent = '';
    return;
  }
  document.getElementById('volume-fill').style.width = percent + '%';
  document.getElementById('volume-knob').style.left = percent + '%';
  document.getElementById('volume-readout').textContent = percent;
}

function sendVolume(percent, force) {
  if (!statusValid) {
    return;
  }
  const now = Date.now();
  if (!force && now - lastVolumeSendTime < 150) {
    return;
  }
  lastVolumeSendTime = now;
  fetch('/api/zone/' + activeZoneId + '/volume?percent=' + percent).catch(function() {
  });
}

const volumeScrubber = document.getElementById('volume-scrubber');

function handleVolumePointer(event, force) {
  const fraction = scrubberFraction(volumeScrubber, event.clientX);
  const percent = Math.round(fraction * 100);
  renderVolume(percent);
  if (zonesById[activeZoneId]) {
    zonesById[activeZoneId].volume = percent;
  }
  sendVolume(percent, force);
}

volumeScrubber.addEventListener('pointerdown', function(event) {
  draggingVolume = true;
  volumeScrubber.setPointerCapture(event.pointerId);
  handleVolumePointer(event, true);
});
volumeScrubber.addEventListener('pointermove', function(event) {
  if (!draggingVolume) {
    return;
  }
  handleVolumePointer(event, false);
});
volumeScrubber.addEventListener('pointerup', function(event) {
  if (!draggingVolume) {
    return;
  }
  draggingVolume = false;
  handleVolumePointer(event, true);
  renderZoneChips();
});
volumeScrubber.addEventListener('pointercancel', function() {
  draggingVolume = false;
});

// ===== room dropdown =====

const roomDropdown = document.getElementById('room-dropdown');

document.getElementById('room-dropdown-button').onclick = function(event) {
  event.stopPropagation();
  roomDropdown.classList.toggle('open');
  renderRoomMenu();
};

document.addEventListener('click', function() {
  roomDropdown.classList.remove('open');
});

function selectZone(zoneId) {
  activeZoneId = zoneId;
  fastPollDeadline = null;
  lastTrackKey = null;
  trackEndPollSent = false;
  roomDropdown.classList.remove('open');
  history.replaceState(null, '', '/?zone=' + zoneId);
  const zone = zonesById[zoneId];
  if (zone) {
    document.getElementById('room-dropdown-name').textContent = zone.name;
  }
  pollActiveZone();
  renderRoomMenu();
  renderZoneChips();
}

function renderRoomMenu() {
  const menu = document.getElementById('room-menu');
  menu.textContent = '';
  sortedZoneIds().forEach(function(zoneId) {
    const zone = zonesById[zoneId];
    const row = document.createElement('button');
    row.className = 'room-menu-row';
    if (zoneId === activeZoneId) {
      row.className += ' selected';
    }
    if (zone.is_on) {
      row.className += ' on';
    }
    const dot = document.createElement('span');
    dot.className = 'menu-dot';
    row.appendChild(dot);
    row.appendChild(document.createTextNode(zone.name));
    row.onclick = function(event) {
      event.stopPropagation();
      selectZone(zoneId);
    };
    menu.appendChild(row);
  });
}

function sortedZoneIds() {
  return Object.keys(zonesById).map(Number).sort(function(a, b) { return a - b; });
}

// ===== zone (room) chips =====

function renderZoneChips() {
  const container = document.getElementById('zone-chips');
  container.textContent = '';
  sortedZoneIds().forEach(function(zoneId) {
    const zone = zonesById[zoneId];
    const chip = document.createElement('button');
    chip.className = zone.is_on ? 'chip on' : 'chip';

    const dot = document.createElement('span');
    dot.className = 'chip-dot';
    chip.appendChild(dot);

    const name = document.createElement('span');
    name.textContent = zone.name;
    chip.appendChild(name);

    const meta = document.createElement('span');
    meta.className = 'chip-meta';
    if (zone.is_on) {
      meta.textContent = (zone.volume === null || zone.volume === undefined) ? '' : zone.volume;
    } else {
      meta.textContent = 'off';
    }
    chip.appendChild(meta);

    chip.onclick = function() {
      toggleZoneChip(zoneId);
    };
    container.appendChild(chip);
  });
}

function toggleZoneChip(zoneId) {
  const zone = zonesById[zoneId];
  if (zone.is_on) {
    zone.is_on = false;
    renderZoneChips();
    sendAction(zoneId, 'zone_off').then(pollAllZones);
  } else {
    zone.is_on = true;
    renderZoneChips();
    let groupSource = null;
    if (activeStatus && activeStatus.source) {
      groupSource = activeStatus.source;
    }
    sendAction(zoneId, 'zone_on').then(function() {
      if (groupSource !== null && zoneId !== activeZoneId) {
        return sendAction(zoneId, 'set_source', 'source_id=' + groupSource);
      }
    }).then(pollAllZones);
  }
}

// ===== source chips =====

function renderSourceChips() {
  const container = document.getElementById('source-chips');
  container.textContent = '';
  sources.forEach(function(source) {
    const chip = document.createElement('button');
    const isCurrent = activeStatus && activeStatus.is_on && activeStatus.source === source.id;
    chip.className = isCurrent ? 'chip on' : 'chip';

    const dot = document.createElement('span');
    dot.className = 'chip-dot';
    chip.appendChild(dot);

    const name = document.createElement('span');
    name.textContent = source.name;
    chip.appendChild(name);

    chip.onclick = function() {
      sendAction(activeZoneId, 'set_source', 'source_id=' + source.id).then(pollActiveZone);
    };
    container.appendChild(chip);
  });
}

function loadSources() {
  fetch('/api/sources')
    .then(function(response) {
      if (!response.ok) {
        throw response.status;
      }
      return response.json();
    })
    .then(function(data) {
      sources = data.sources;
      renderSourceChips();
    })
    .catch(function() {
      sources = [];
    });
}

loadSources();

// ===== favorites overlay =====


document.getElementById('favorites-button').onclick = function() {
  favoritesOverlay.classList.add('open');
  if (favorites === null) {
    loadFavorites();
  } else {
    renderFavorites();
  }
};
document.getElementById('favorites-close').onclick = function() {
  favoritesOverlay.classList.remove('open');
};
favoritesOverlay.onclick = function() {
  favoritesOverlay.classList.remove('open');
};
document.getElementById('favorites-panel').onclick = function(event) {
  event.stopPropagation();
};

function loadFavorites() {
  fetch('/api/zone/' + activeZoneId + '/favorites')
    .then(function(response) {
      if (!response.ok) {
        throw response.status;
      }
      return response.json();
    })
    .then(function(data) {
      favorites = data.favorites;
      renderFavorites();
    })
    .catch(function() {
      favorites = null;
    });
}

function renderFavorites() {
  document.getElementById('favorites-count').textContent = favorites.length + ' saved';
  const list = document.getElementById('favorites-list');
  list.textContent = '';
  let currentTitle = null;
  let currentStation = null;
  if (activeStatus) {
    currentTitle = activeStatus.title;
    currentStation = activeStatus.album;
  }
  favorites.forEach(function(favorite) {
    const item = document.createElement('button');
    item.className = 'favorite-item';
    let isCurrent = false;
    if (currentTitle && favorite.name === currentTitle) {
      isCurrent = true;
    }
    if (currentStation) {
      // favorite names may carry a channel suffix, e.g. "Alt2K (27)" for station "Alt2K"
      if (favorite.name === currentStation || favorite.name.indexOf(currentStation + ' ') === 0) {
        isCurrent = true;
      }
    }
    if (isCurrent) {
      item.className += ' current';
    }

    const dot = document.createElement('span');
    dot.className = 'favorite-dot';
    item.appendChild(dot);

    const name = document.createElement('span');
    name.className = 'favorite-name';
    name.textContent = favorite.name;
    item.appendChild(name);

    item.onclick = function() {
      sendAction(activeZoneId, 'play_favorite', 'favorite_id=' + encodeURIComponent(favorite.id))
        .then(pollActiveZone);
      favoritesOverlay.classList.remove('open');
    };
    list.appendChild(item);
  });
}

// ===== startup =====

renderRoomMenu();
renderZoneChips();
if (activeZoneId !== null && zonesById[activeZoneId]) {
  document.getElementById('room-dropdown-name').textContent = zonesById[activeZoneId].name;
}
pollActiveZone();
pollAllZones();
setInterval(pollAllZones, 2500);
