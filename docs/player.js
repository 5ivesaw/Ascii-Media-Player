'use strict';

const config = window.ASCII_MEDIA_PLAYER_CONFIG || {
  version: '2.1.0',
  repositoryUrl: 'https://github.com/5ivesaw/Ascii-Media-Player',
  siteUrl: 'https://5ivesaw.github.io/Ascii-Media-Player/'
};

const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

const audio = $('#audio');
const asciiScreen = $('#asciiScreen');
const asciiStage = $('#asciiStage');
const dropZone = $('#dropZone');
const fileInput = $('#fileInput');
const playButton = $('#playButton');
const previousButton = $('#previousButton');
const nextButton = $('#nextButton');
const shuffleButton = $('#shuffleButton');
const repeatButton = $('#repeatButton');
const clearQueueButton = $('#clearQueueButton');
const demoButton = $('#demoButton');
const installButton = $('#installButton');
const fullscreenButton = $('#fullscreenButton');
const seek = $('#seek');
const volume = $('#volume');
const volumeValue = $('#volumeValue');
const visualMode = $('#visualMode');
const density = $('#density');
const themeSelect = $('#themeSelect');
const currentTimeLabel = $('#currentTime');
const durationLabel = $('#duration');
const trackLabel = $('#trackLabel');
const trackDetail = $('#trackDetail');
const signalStatus = $('#signalStatus');
const statusLight = $('#statusLight');
const queueList = $('#queueList');
const queueCount = $('#queueCount');
const dropHint = $('#dropHint');
const toast = $('#toast');
const menuToggle = $('#menuToggle');
const siteNav = $('#siteNav');
const heroSignal = $('#heroSignal');

let audioContext;
let analyser;
let mediaSource;
let animationFrame = 0;
let queue = [];
let currentIndex = -1;
let repeatEnabled = false;
let shuffleEnabled = false;
let demoNodes = [];
let demoTimer = 0;
let demoActive = false;
let deferredInstallPrompt = null;
let previousVolume = 0.75;
let toastTimer = 0;

const charset = ' .,:;irsXA253hMHGS#9B&@';
const audioExtension = /\.(mp3|wav|ogg|oga|flac|m4a|aac|webm|opus|wma)$/i;

function showToast(message, duration = 2400) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add('visible');
  toastTimer = window.setTimeout(() => toast.classList.remove('visible'), duration);
}

function setStatus(label, state = 'idle') {
  signalStatus.textContent = label.toUpperCase();
  statusLight.classList.toggle('live', state === 'live');
  statusLight.classList.toggle('error', state === 'error');
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00';
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return 'Unknown size';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / (1024 ** index);
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

function updateRange(input) {
  const min = Number(input.min || 0);
  const max = Number(input.max || 100);
  const value = Number(input.value);
  const progress = max === min ? 0 : ((value - min) / (max - min)) * 100;
  input.style.setProperty('--range-progress', `${progress}%`);
}

function ensureAudioGraph() {
  if (!audioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error('Web Audio API is not supported by this browser.');
    audioContext = new AudioContextClass();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.82;
    mediaSource = audioContext.createMediaElementSource(audio);
    mediaSource.connect(analyser);
    analyser.connect(audioContext.destination);
  }
  if (audioContext.state === 'suspended') audioContext.resume();
}

function visualizerDimensions() {
  const stageWidth = asciiStage.clientWidth || window.innerWidth;
  const densityMode = density.value;
  let width;
  let height;

  if (stageWidth < 460) {
    width = densityMode === 'dense' ? 64 : densityMode === 'compact' ? 42 : 52;
    height = densityMode === 'dense' ? 27 : densityMode === 'compact' ? 18 : 22;
  } else if (stageWidth < 760) {
    width = densityMode === 'dense' ? 94 : densityMode === 'compact' ? 58 : 76;
    height = densityMode === 'dense' ? 31 : densityMode === 'compact' ? 20 : 26;
  } else {
    width = densityMode === 'dense' ? 116 : densityMode === 'compact' ? 74 : 96;
    height = densityMode === 'dense' ? 34 : densityMode === 'compact' ? 23 : 29;
  }

  return { width, height };
}

function renderSpectrum(frequencyData, width, height) {
  const usableBins = Math.floor(frequencyData.length * 0.72);
  const columnLevels = new Array(width).fill(0);

  for (let column = 0; column < width; column += 1) {
    const start = Math.floor(((column / width) ** 1.75) * usableBins);
    const end = Math.max(start + 1, Math.floor((((column + 1) / width) ** 1.75) * usableBins));
    let sum = 0;
    for (let index = start; index < end; index += 1) sum += frequencyData[index];
    const raw = sum / Math.max(1, end - start) / 255;
    columnLevels[column] = Math.min(1, raw * 1.2);
  }

  const lines = [];
  for (let row = height - 1; row >= 0; row -= 1) {
    const threshold = row / height;
    let line = '';
    for (let column = 0; column < width; column += 1) {
      const level = columnLevels[column];
      if (level >= threshold) {
        const depth = Math.min(1, Math.max(0, (level - threshold) * 2.8 + 0.16));
        const charIndex = Math.max(1, Math.floor(depth * (charset.length - 1)));
        line += charset[charIndex];
      } else if (Math.abs(level - threshold) < 0.022) {
        line += '.';
      } else {
        line += ' ';
      }
    }
    lines.push(line);
  }
  return lines.join('\n');
}

function renderWaveform(timeData, width, height) {
  const grid = Array.from({ length: height }, () => Array(width).fill(' '));
  const middle = Math.floor(height / 2);

  for (let column = 0; column < width; column += 1) {
    const sampleIndex = Math.floor((column / Math.max(1, width - 1)) * (timeData.length - 1));
    const normalized = (timeData[sampleIndex] - 128) / 128;
    const row = Math.max(0, Math.min(height - 1, Math.round(middle - normalized * (height * 0.43))));
    grid[row][column] = Math.abs(normalized) > 0.56 ? '@' : Math.abs(normalized) > 0.28 ? '#' : '*';

    if (column > 0) {
      const previousSampleIndex = Math.floor(((column - 1) / Math.max(1, width - 1)) * (timeData.length - 1));
      const previousNormalized = (timeData[previousSampleIndex] - 128) / 128;
      const previousRow = Math.max(0, Math.min(height - 1, Math.round(middle - previousNormalized * (height * 0.43))));
      const start = Math.min(row, previousRow);
      const end = Math.max(row, previousRow);
      for (let bridge = start + 1; bridge < end; bridge += 1) grid[bridge][column] = '|';
    }
  }

  for (let column = 0; column < width; column += 2) {
    if (grid[middle][column] === ' ') grid[middle][column] = '.';
  }

  return grid.map((line) => line.join('')).join('\n');
}

function renderVisualizer() {
  if (!analyser) return;
  const { width, height } = visualizerDimensions();

  if (visualMode.value === 'waveform') {
    const timeData = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(timeData);
    asciiScreen.textContent = renderWaveform(timeData, width, height);
  } else {
    const frequencyData = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(frequencyData);
    asciiScreen.textContent = renderSpectrum(frequencyData, width, height);
  }

  animationFrame = requestAnimationFrame(renderVisualizer);
}

function startVisualizer() {
  ensureAudioGraph();
  cancelAnimationFrame(animationFrame);
  renderVisualizer();
  setStatus('Live', 'live');
}

function stopVisualizer(status = 'Paused') {
  cancelAnimationFrame(animationFrame);
  animationFrame = 0;
  setStatus(status);
}

function stopDemo() {
  clearTimeout(demoTimer);
  demoNodes.forEach((node) => {
    try { node.stop?.(); } catch (_) { /* Node has already stopped. */ }
    try { node.disconnect?.(); } catch (_) { /* Node has already disconnected. */ }
  });
  demoNodes = [];
  demoActive = false;
}

function isAudioFile(file) {
  return Boolean(file && ((file.type && file.type.startsWith('audio/')) || audioExtension.test(file.name)));
}

function queueItemDetail(item) {
  const type = item.file.type ? item.file.type.replace('audio/', '').toUpperCase() : 'AUDIO';
  return `${type} · ${formatBytes(item.file.size)}`;
}

function renderQueue() {
  queueList.replaceChildren();
  queue.forEach((item, index) => {
    const li = document.createElement('li');
    li.className = `queue-item${index === currentIndex ? ' active' : ''}`;
    li.dataset.index = String(index);

    const trackButton = document.createElement('button');
    trackButton.type = 'button';
    trackButton.className = 'queue-track';
    trackButton.title = `Play ${item.file.name}`;

    const name = document.createElement('strong');
    name.textContent = item.file.name;
    const detail = document.createElement('span');
    detail.textContent = item.duration ? `${formatTime(item.duration)} · ${queueItemDetail(item)}` : queueItemDetail(item);
    trackButton.append(name, detail);
    trackButton.addEventListener('click', () => selectTrack(index, true));

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'queue-remove';
    removeButton.setAttribute('aria-label', `Remove ${item.file.name} from queue`);
    removeButton.textContent = '×';
    removeButton.addEventListener('click', () => removeTrack(index));

    li.append(trackButton, removeButton);
    queueList.append(li);
  });

  queueCount.textContent = `${queue.length} ${queue.length === 1 ? 'TRACK' : 'TRACKS'}`;
  dropHint.hidden = queue.length > 0;
  clearQueueButton.disabled = queue.length === 0;
  playButton.disabled = currentIndex < 0;
  previousButton.disabled = queue.length < 2;
  nextButton.disabled = queue.length < 2;
}

function addFiles(fileList) {
  const files = Array.from(fileList || []);
  const valid = files.filter(isAudioFile);
  const rejected = files.length - valid.length;

  valid.forEach((file) => {
    queue.push({
      id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID?.() || Math.random()}`,
      file,
      url: URL.createObjectURL(file),
      duration: 0
    });
  });

  if (currentIndex < 0 && queue.length) selectTrack(0, false);
  renderQueue();

  if (valid.length) showToast(`${valid.length} ${valid.length === 1 ? 'track' : 'tracks'} added locally.`);
  if (rejected) showToast(`${rejected} unsupported ${rejected === 1 ? 'file was' : 'files were'} ignored.`);
}

function selectTrack(index, autoplay = false) {
  if (index < 0 || index >= queue.length) return;
  stopDemo();
  const item = queue[index];
  const wasPlaying = !audio.paused;
  audio.pause();
  currentIndex = index;
  audio.src = item.url;
  audio.load();
  trackLabel.textContent = item.file.name;
  trackDetail.textContent = queueItemDetail(item);
  currentTimeLabel.textContent = '0:00';
  durationLabel.textContent = item.duration ? formatTime(item.duration) : '0:00';
  seek.value = '0';
  updateRange(seek);
  setStatus('Ready');
  renderQueue();

  if (autoplay || wasPlaying) {
    audio.play().catch((error) => {
      setStatus('Playback blocked', 'error');
      showToast(error.message || 'Playback could not start.');
    });
  }
}

function removeTrack(index) {
  if (index < 0 || index >= queue.length) return;
  const removingCurrent = index === currentIndex;
  const [removed] = queue.splice(index, 1);
  URL.revokeObjectURL(removed.url);

  if (!queue.length) {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    currentIndex = -1;
    trackLabel.textContent = 'No track loaded';
    trackDetail.textContent = 'Choose local audio or start the generated signal demo.';
    currentTimeLabel.textContent = '0:00';
    durationLabel.textContent = '0:00';
    seek.value = '0';
    stopVisualizer('Idle');
  } else if (removingCurrent) {
    currentIndex = Math.min(index, queue.length - 1);
    selectTrack(currentIndex, false);
  } else if (index < currentIndex) {
    currentIndex -= 1;
  }

  renderQueue();
}

function clearQueue() {
  audio.pause();
  stopDemo();
  queue.forEach((item) => URL.revokeObjectURL(item.url));
  queue = [];
  currentIndex = -1;
  audio.removeAttribute('src');
  audio.load();
  trackLabel.textContent = 'No track loaded';
  trackDetail.textContent = 'Choose local audio or start the generated signal demo.';
  currentTimeLabel.textContent = '0:00';
  durationLabel.textContent = '0:00';
  seek.value = '0';
  updateRange(seek);
  asciiScreen.textContent = '\n\n                              DROP AUDIO TO BEGIN\n\n                     LOCAL FILES NEVER LEAVE THIS DEVICE\n\n';
  stopVisualizer('Idle');
  renderQueue();
  showToast('Local queue cleared.');
}

function nextTrack(autoplay = true) {
  if (!queue.length) return;
  if (shuffleEnabled && queue.length > 1) {
    let next = currentIndex;
    while (next === currentIndex) next = Math.floor(Math.random() * queue.length);
    selectTrack(next, autoplay);
    return;
  }
  selectTrack((currentIndex + 1) % queue.length, autoplay);
}

function previousTrack() {
  if (!queue.length) return;
  if (audio.currentTime > 4) {
    audio.currentTime = 0;
    return;
  }
  selectTrack((currentIndex - 1 + queue.length) % queue.length, true);
}

async function togglePlayback() {
  if (currentIndex < 0) return;
  try {
    ensureAudioGraph();
    stopDemo();
    if (audio.paused) await audio.play();
    else audio.pause();
  } catch (error) {
    setStatus('Audio error', 'error');
    showToast(error.message || 'Audio playback is not available.');
  }
}

async function runDemo() {
  try {
    ensureAudioGraph();
    audio.pause();
    stopDemo();
    demoActive = true;
    const now = audioContext.currentTime;
    const master = audioContext.createGain();
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.075, now + 0.12);
    master.gain.setValueAtTime(0.075, now + 7.4);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 8);
    master.connect(analyser);

    [82.41, 123.47, 164.81, 246.94, 329.63].forEach((frequency, index) => {
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = ['sine', 'triangle', 'sine', 'sawtooth', 'triangle'][index];
      oscillator.frequency.setValueAtTime(frequency, now);
      oscillator.frequency.exponentialRampToValueAtTime(frequency * (1.35 + index * 0.11), now + 8);
      gain.gain.value = 0.2 / (index + 1);
      oscillator.connect(gain);
      gain.connect(master);
      oscillator.start(now + index * 0.045);
      oscillator.stop(now + 8);
      demoNodes.push(oscillator, gain);
    });

    demoNodes.push(master);
    trackLabel.textContent = 'Generated signal sequence';
    trackDetail.textContent = 'Five synthesized oscillators · Eight seconds · No sample file';
    playButton.textContent = 'Play';
    setStatus('Demo live', 'live');
    startVisualizer();

    demoTimer = window.setTimeout(() => {
      stopDemo();
      if (currentIndex >= 0) {
        const item = queue[currentIndex];
        trackLabel.textContent = item.file.name;
        trackDetail.textContent = queueItemDetail(item);
        stopVisualizer('Ready');
      } else {
        trackLabel.textContent = 'No track loaded';
        trackDetail.textContent = 'Choose local audio or start the generated signal demo.';
        stopVisualizer('Idle');
      }
    }, 8100);
  } catch (error) {
    setStatus('Demo error', 'error');
    showToast(error.message || 'The signal demo could not start.');
  }
}

function applyConfig() {
  const repositoryUrl = config.repositoryUrl.replace(/\/$/, '');
  const siteUrl = config.siteUrl.endsWith('/') ? config.siteUrl : `${config.siteUrl}/`;

  $$('[data-repo-link]').forEach((link) => { link.href = repositoryUrl; });
  $$('[data-issues-link]').forEach((link) => { link.href = `${repositoryUrl}/issues`; });
  $$('[data-repo-install-link]').forEach((link) => { link.href = `${repositoryUrl}#desktop-installation`; });

  const installCode = $('#installCode code');
  if (installCode) {
    const cloneUrl = `${repositoryUrl}.git`;
    const repositoryName = repositoryUrl.split('/').filter(Boolean).pop() || 'Ascii-Media-Player';
    installCode.textContent = `git clone ${cloneUrl}\ncd ${repositoryName}\npython -m pip install -r requirements.txt\npython app.py "/path/to/music"`;
  }

  const appVersion = $('#appVersion');
  if (appVersion) appVersion.textContent = `VERSION ${config.version || '2.1.0'}`;

  document.title = 'ASCII Media Player — Local Audio Visualizer';
  window.__ASCII_SITE_URL__ = siteUrl;
}

function animateHeroSignal() {
  const width = window.innerWidth < 520 ? 58 : 78;
  const height = window.innerWidth < 520 ? 21 : 29;
  const time = performance.now() / 720;
  const lines = [];

  for (let row = height - 1; row >= 0; row -= 1) {
    let line = '';
    for (let column = 0; column < width; column += 1) {
      const x = column / width;
      const wave = 0.16
        + 0.2 * Math.sin(time * 0.8 + x * 7.5) ** 2
        + 0.38 * Math.exp(-((x - (0.25 + Math.sin(time * 0.34) * 0.08)) ** 2) / 0.012)
        + 0.28 * Math.exp(-((x - (0.68 + Math.cos(time * 0.28) * 0.1)) ** 2) / 0.02);
      const threshold = row / height;
      if (wave > threshold) {
        const charIndex = Math.min(charset.length - 1, Math.max(1, Math.floor((wave - threshold + 0.14) * charset.length)));
        line += charset[charIndex];
      } else {
        line += Math.abs(wave - threshold) < 0.018 ? '.' : ' ';
      }
    }
    lines.push(line);
  }

  heroSignal.textContent = lines.join('\n');
  requestAnimationFrame(animateHeroSignal);
}

fileInput.addEventListener('change', () => {
  addFiles(fileInput.files);
  fileInput.value = '';
});

playButton.addEventListener('click', togglePlayback);
previousButton.addEventListener('click', previousTrack);
nextButton.addEventListener('click', () => nextTrack(true));
clearQueueButton.addEventListener('click', clearQueue);
demoButton.addEventListener('click', runDemo);

shuffleButton.addEventListener('click', () => {
  shuffleEnabled = !shuffleEnabled;
  shuffleButton.setAttribute('aria-pressed', String(shuffleEnabled));
  showToast(`Shuffle ${shuffleEnabled ? 'enabled' : 'disabled'}.`);
});

repeatButton.addEventListener('click', () => {
  repeatEnabled = !repeatEnabled;
  audio.loop = repeatEnabled;
  repeatButton.setAttribute('aria-pressed', String(repeatEnabled));
  showToast(`Repeat ${repeatEnabled ? 'enabled' : 'disabled'}.`);
});

audio.addEventListener('play', () => {
  playButton.textContent = 'Pause';
  startVisualizer();
});

audio.addEventListener('pause', () => {
  playButton.textContent = 'Play';
  if (!demoActive) stopVisualizer(currentIndex >= 0 ? 'Paused' : 'Idle');
});

audio.addEventListener('ended', () => {
  playButton.textContent = 'Play';
  if (!repeatEnabled && queue.length > 1) nextTrack(true);
  else if (!repeatEnabled) stopVisualizer('Complete');
});

audio.addEventListener('loadedmetadata', () => {
  durationLabel.textContent = formatTime(audio.duration);
  if (currentIndex >= 0 && queue[currentIndex]) {
    queue[currentIndex].duration = audio.duration;
    renderQueue();
  }
});

audio.addEventListener('timeupdate', () => {
  currentTimeLabel.textContent = formatTime(audio.currentTime);
  seek.value = audio.duration ? String(Math.round((audio.currentTime / audio.duration) * 1000)) : '0';
  updateRange(seek);
});

audio.addEventListener('error', () => {
  setStatus('Decode error', 'error');
  showToast('This browser could not decode the selected audio file.');
});

seek.addEventListener('input', () => {
  if (audio.duration) audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
  updateRange(seek);
});

volume.addEventListener('input', () => {
  audio.volume = Number(volume.value);
  if (audio.volume > 0) previousVolume = audio.volume;
  volumeValue.value = String(Math.round(audio.volume * 100));
  updateRange(volume);
  localStorage.setItem('amp-volume', volume.value);
});

visualMode.addEventListener('change', () => {
  localStorage.setItem('amp-mode', visualMode.value);
  if (analyser && (!audio.paused || demoActive)) startVisualizer();
});

density.addEventListener('change', () => {
  localStorage.setItem('amp-density', density.value);
  if (analyser && (!audio.paused || demoActive)) startVisualizer();
});

themeSelect.addEventListener('change', () => {
  document.body.dataset.theme = themeSelect.value;
  localStorage.setItem('amp-theme', themeSelect.value);
});

fullscreenButton.addEventListener('click', async () => {
  try {
    if (!document.fullscreenElement) await dropZone.requestFullscreen();
    else await document.exitFullscreen();
  } catch (_) {
    showToast('Fullscreen is not available in this browser.');
  }
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
    dropZone.classList.add('dragging');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
  });
});

dropZone.addEventListener('drop', (event) => addFiles(event.dataTransfer?.files));

document.addEventListener('keydown', (event) => {
  if (event.target.matches('input, button, select, textarea')) return;
  const key = event.key.toLowerCase();

  if (event.code === 'Space') {
    event.preventDefault();
    togglePlayback();
  } else if (event.key === 'ArrowLeft' && currentIndex >= 0) {
    event.preventDefault();
    audio.currentTime = Math.max(0, audio.currentTime - 5);
  } else if (event.key === 'ArrowRight' && currentIndex >= 0) {
    event.preventDefault();
    audio.currentTime = Math.min(audio.duration || Infinity, audio.currentTime + 5);
  } else if (key === 'n') {
    nextTrack(true);
  } else if (key === 'm') {
    if (audio.volume > 0) {
      previousVolume = audio.volume;
      audio.volume = 0;
      volume.value = '0';
    } else {
      audio.volume = previousVolume || 0.75;
      volume.value = String(audio.volume);
    }
    volume.dispatchEvent(new Event('input'));
  } else if (key === 'f') {
    fullscreenButton.click();
  }
});

$$('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(target.innerText);
      showToast('Install commands copied.');
    } catch (_) {
      showToast('Select the commands and copy them manually.');
    }
  });
});

menuToggle.addEventListener('click', () => {
  const open = !siteNav.classList.contains('open');
  siteNav.classList.toggle('open', open);
  menuToggle.setAttribute('aria-expanded', String(open));
  document.body.classList.toggle('menu-open', open);
});

siteNav.addEventListener('click', (event) => {
  if (event.target.matches('a')) {
    siteNav.classList.remove('open');
    menuToggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
  }
});

window.addEventListener('scroll', () => {
  $('.site-header').classList.toggle('scrolled', window.scrollY > 10);
}, { passive: true });

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  installButton.hidden = false;
});

installButton.addEventListener('click', async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  const choice = await deferredInstallPrompt.userChoice;
  showToast(choice.outcome === 'accepted' ? 'Installation started.' : 'Installation cancelled.');
  deferredInstallPrompt = null;
  installButton.hidden = true;
});

window.addEventListener('appinstalled', () => {
  installButton.hidden = true;
  showToast('ASCII Media Player installed.');
});

const savedVolume = Number(localStorage.getItem('amp-volume'));
if (Number.isFinite(savedVolume) && savedVolume >= 0 && savedVolume <= 1) volume.value = String(savedVolume);
audio.volume = Number(volume.value);
previousVolume = audio.volume || 0.75;
volumeValue.value = String(Math.round(audio.volume * 100));
updateRange(volume);
updateRange(seek);

const savedTheme = localStorage.getItem('amp-theme');
if (['ice', 'matrix', 'amber', 'mono'].includes(savedTheme)) themeSelect.value = savedTheme;
document.body.dataset.theme = themeSelect.value;

const savedMode = localStorage.getItem('amp-mode');
if (['spectrum', 'waveform'].includes(savedMode)) visualMode.value = savedMode;
const savedDensity = localStorage.getItem('amp-density');
if (['compact', 'balanced', 'dense'].includes(savedDensity)) density.value = savedDensity;

applyConfig();
renderQueue();
$('#year').textContent = String(new Date().getFullYear());
animateHeroSignal();

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
$$('.reveal').forEach((element) => observer.observe(element));

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('./sw.js');
      registration.addEventListener('updatefound', () => {
        const worker = registration.installing;
        worker?.addEventListener('statechange', () => {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            showToast('A site update is ready. Reload to apply it.', 5000);
          }
        });
      });
    } catch (_) {
      // The application remains fully usable without service worker support.
    }
  });
}
