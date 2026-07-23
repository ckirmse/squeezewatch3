// Amplr player client logic.
// Expects globals from the template: bootstrapZones (array), initialZoneId (int or null).

var activeZoneId = initialZoneId;
var zonesById = {};
var activeStatus = null;
var sources = [];
var favorites = null;

var draggingVolume = false;
var lastVolumeSendTime = 0;

var progressBase = null;
var progressBaseTime = null;
var progressDuration = null;
var progressPlaying = false;
var progressLastDisplayedSecond = null;
var progressLastMode = null;

// Reconciliation tuning: differences larger than the snap threshold are treated
// as real discontinuities (seek, track change); smaller ones are slewed away
// gradually so the displayed clock never visibly skips or jumps back.
var PROGRESS_SNAP_THRESHOLD_SECONDS = 2;
var PROGRESS_SLEW_GAIN = 0.1;

bootstrapZones.forEach(function(zone) {
  zonesById[zone.id] = zone;
});

function clampFraction(value) {
  return Math.max(0, Math.min(1, value));
}

function formatTime(seconds) {
  seconds = Math.max(0, Math.floor(seconds));
  var minutes = Math.floor(seconds / 60);
  var remainder = seconds % 60;
  return minutes + ':' + (remainder < 10 ? '0' : '') + remainder;
}

function sendAction(zoneId, action, extraQuery) {
  var url = '/api/zone/' + zoneId + '/action?action=' + action;
  if (extraQuery) {
    url += '&' + extraQuery;
  }
  return fetch(url);
}

// ===== now playing / progress =====

function currentLocalPosition() {
  if (progressBase === null) {
    return null;
  }
  var elapsed = progressBase;
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
  var seekBlock = document.getElementById('seek-block');
  if (progressBase === null || progressDuration === null) {
    seekBlock.classList.add('hidden');
    return;
  }
  var elapsed = currentLocalPosition();
  if (elapsed < 0) {
    elapsed = 0;
  }
  if (elapsed > progressDuration) {
    elapsed = progressDuration;
  }
  var displayedSecond = Math.floor(elapsed);
  if (progressPlaying && progressLastDisplayedSecond !== null && displayedSecond < progressLastDisplayedSecond) {
    displayedSecond = progressLastDisplayedSecond;
  }
  progressLastDisplayedSecond = displayedSecond;
  var percent = clampFraction(elapsed / progressDuration) * 100;
  seekBlock.classList.remove('hidden');
  document.getElementById('seek-fill').style.width = percent + '%';
  document.getElementById('seek-knob').style.left = percent + '%';
  document.getElementById('seek-elapsed').textContent = formatTime(displayedSecond);
  document.getElementById('seek-total').textContent = formatTime(progressDuration);
}

setInterval(renderProgress, 250);

function renderStatus(data) {
  activeStatus = data;

  var nowPlayingContent = document.getElementById('now-playing-content');
  if (data.is_on) {
    nowPlayingContent.classList.remove('hidden');
  } else {
    nowPlayingContent.classList.add('hidden');
  }

  var controlsDisabled = !data.is_on;
  document.getElementById('play-button').disabled = controlsDisabled;
  document.getElementById('prev-button').disabled = controlsDisabled;
  document.getElementById('next-button').disabled = controlsDisabled;
  document.getElementById('favorites-button').disabled = controlsDisabled;
  var volumeScrubberElement = document.getElementById('volume-scrubber');
  if (controlsDisabled) {
    volumeScrubberElement.classList.add('disabled');
  } else {
    volumeScrubberElement.classList.remove('disabled');
  }

  var title = data.title;
  if (!title) {
    title = data.lines[3];
  }
  var artist = data.artist;
  if (!artist) {
    artist = data.lines[2];
  }
  var station = data.album;
  if (!station) {
    station = data.lines[1];
  }
  if (!title) {
    title = '—';
  }
  document.getElementById('track-title').textContent = title;
  document.getElementById('track-artist').textContent = artist || ' ';
  document.getElementById('station-name').textContent = station;

  var playButton = document.getElementById('play-button');
  playButton.className = 'round-button play-button mode-' + data.mode;

  var artBezel = document.getElementById('art-bezel');
  if (data.mode === 'play') {
    artBezel.classList.add('playing');
  } else {
    artBezel.classList.remove('playing');
  }

  var artworkImage = document.getElementById('artwork-image');
  if (data.artwork_url) {
    if (artworkImage.getAttribute('src') !== data.artwork_url) {
      artworkImage.src = data.artwork_url;
    }
  } else {
    artworkImage.removeAttribute('src');
    artworkImage.classList.remove('visible');
  }

  var previousDuration = progressDuration;
  var previousMode = progressLastMode;
  var localPosition = currentLocalPosition();

  progressPlaying = (data.mode === 'play');
  progressDuration = data.duration_sec;
  progressLastMode = data.mode;

  if (data.position_sec !== null && data.position_sec !== undefined && data.duration_sec) {
    // The server position sample only advances while playing; when paused or
    // stopped its age grows but the true position does not.
    var serverPosition = data.position_sec;
    if (data.mode === 'play') {
      serverPosition += (data.position_age_sec || 0);
    }
    var mustSnap = false;
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
  var dropdownDot = document.getElementById('room-dropdown-dot');
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

var artworkImageElement = document.getElementById('artwork-image');
artworkImageElement.onload = function() {
  artworkImageElement.classList.add('visible');
};
artworkImageElement.onerror = function() {
  artworkImageElement.classList.remove('visible');
};

function pollActiveZone() {
  if (activeZoneId === null) {
    return;
  }
  fetch('/api/zone/' + activeZoneId + '/status')
    .then(function(response) { return response.json(); })
    .then(function(data) {
      if (data.zone_id === activeZoneId) {
        renderStatus(data);
      }
    });
}

function pollAllZones() {
  fetch('/api/zones')
    .then(function(response) { return response.json(); })
    .then(function(data) {
      data.zones.forEach(function(zone) {
        zonesById[zone.id] = zone;
      });
      renderZoneChips();
      renderRoomMenu();
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
  var rect = scrubber.querySelector('.scrubber-track').getBoundingClientRect();
  return clampFraction((clientX - rect.left) / rect.width);
}

var seekScrubber = document.getElementById('seek-scrubber');
seekScrubber.addEventListener('pointerdown', function(event) {
  if (!progressDuration) {
    return;
  }
  var fraction = scrubberFraction(seekScrubber, event.clientX);
  var seconds = Math.round(fraction * progressDuration);
  snapProgress(seconds);
  renderProgress();
  fetch('/api/zone/' + activeZoneId + '/seek?seconds=' + seconds);
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
  var now = Date.now();
  if (!force && now - lastVolumeSendTime < 150) {
    return;
  }
  lastVolumeSendTime = now;
  fetch('/api/zone/' + activeZoneId + '/volume?percent=' + percent);
}

var volumeScrubber = document.getElementById('volume-scrubber');

function handleVolumePointer(event, force) {
  var fraction = scrubberFraction(volumeScrubber, event.clientX);
  var percent = Math.round(fraction * 100);
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

var roomDropdown = document.getElementById('room-dropdown');

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
  roomDropdown.classList.remove('open');
  history.replaceState(null, '', '/?zone=' + zoneId);
  var zone = zonesById[zoneId];
  if (zone) {
    document.getElementById('room-dropdown-name').textContent = zone.name;
  }
  pollActiveZone();
  renderRoomMenu();
  renderZoneChips();
}

function renderRoomMenu() {
  var menu = document.getElementById('room-menu');
  menu.textContent = '';
  sortedZoneIds().forEach(function(zoneId) {
    var zone = zonesById[zoneId];
    var row = document.createElement('button');
    row.className = 'room-menu-row';
    if (zoneId === activeZoneId) {
      row.className += ' selected';
    }
    if (zone.is_on) {
      row.className += ' on';
    }
    var dot = document.createElement('span');
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
  var container = document.getElementById('zone-chips');
  container.textContent = '';
  sortedZoneIds().forEach(function(zoneId) {
    var zone = zonesById[zoneId];
    var chip = document.createElement('button');
    chip.className = zone.is_on ? 'chip on' : 'chip';

    var dot = document.createElement('span');
    dot.className = 'chip-dot';
    chip.appendChild(dot);

    var name = document.createElement('span');
    name.textContent = zone.name;
    chip.appendChild(name);

    var meta = document.createElement('span');
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
  var zone = zonesById[zoneId];
  if (zone.is_on) {
    zone.is_on = false;
    renderZoneChips();
    sendAction(zoneId, 'zone_off').then(pollAllZones);
  } else {
    zone.is_on = true;
    renderZoneChips();
    var groupSource = null;
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
  var container = document.getElementById('source-chips');
  container.textContent = '';
  sources.forEach(function(source) {
    var chip = document.createElement('button');
    var isCurrent = activeStatus && activeStatus.is_on && activeStatus.source === source.id;
    chip.className = isCurrent ? 'chip on' : 'chip';

    var dot = document.createElement('span');
    dot.className = 'chip-dot';
    chip.appendChild(dot);

    var name = document.createElement('span');
    name.textContent = source.name;
    chip.appendChild(name);

    chip.onclick = function() {
      sendAction(activeZoneId, 'set_source', 'source_id=' + source.id).then(pollActiveZone);
    };
    container.appendChild(chip);
  });
}

fetch('/api/sources')
  .then(function(response) { return response.json(); })
  .then(function(data) {
    sources = data.sources;
    renderSourceChips();
  });

// ===== favorites overlay =====

var favoritesOverlay = document.getElementById('favorites-overlay');

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
    .then(function(response) { return response.json(); })
    .then(function(data) {
      favorites = data.favorites;
      renderFavorites();
    });
}

function renderFavorites() {
  document.getElementById('favorites-count').textContent = favorites.length + ' saved';
  var list = document.getElementById('favorites-list');
  list.textContent = '';
  var currentTitle = null;
  var currentStation = null;
  if (activeStatus) {
    currentTitle = activeStatus.title;
    currentStation = activeStatus.album;
  }
  favorites.forEach(function(favorite) {
    var item = document.createElement('button');
    item.className = 'favorite-item';
    var isCurrent = false;
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

    var dot = document.createElement('span');
    dot.className = 'favorite-dot';
    item.appendChild(dot);

    var name = document.createElement('span');
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
setInterval(pollActiveZone, 1000);
setInterval(pollAllZones, 2500);
