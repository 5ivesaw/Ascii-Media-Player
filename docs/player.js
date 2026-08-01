const audio = document.querySelector('#audio');
const fileInput = document.querySelector('#fileInput');
const playButton = document.querySelector('#playButton');
const demoButton = document.querySelector('#demoButton');
const fullscreenButton = document.querySelector('#fullscreenButton');
const seek = document.querySelector('#seek');
const volume = document.querySelector('#volume');
const currentTimeLabel = document.querySelector('#currentTime');
const durationLabel = document.querySelector('#duration');
const trackLabel = document.querySelector('#trackLabel');
const signalStatus = document.querySelector('#signalStatus');
const asciiScreen = document.querySelector('#asciiScreen');
const dropZone = document.querySelector('#dropZone');

let audioContext;
let analyser;
let sourceNode;
let animationFrame;
let demoNodes = [];
let objectUrl;
let loadedFile = false;

const charset = ' .,:;irsXA253hMHGS#9B&@';

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00';
  const value = Math.max(0, Math.floor(seconds));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
}

function ensureAudioGraph() {
  if (!audioContext) {
    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.82;
    sourceNode = audioContext.createMediaElementSource(audio);
    sourceNode.connect(analyser);
    analyser.connect(audioContext.destination);
  }
  if (audioContext.state === 'suspended') audioContext.resume();
}

function visualizerDimensions() {
  const width = window.innerWidth < 600 ? 54 : window.innerWidth < 900 ? 72 : 96;
  const height = window.innerWidth < 600 ? 24 : 28;
  return { width, height };
}

function renderSpectrum() {
  if (!analyser) return;
  const frequencyData = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(frequencyData);
  const { width, height } = visualizerDimensions();
  const usableBins = Math.floor(frequencyData.length * 0.72);
  const lines = [];

  for (let row = height - 1; row >= 0; row -= 1) {
    let line = '';
    for (let column = 0; column < width; column += 1) {
      const start = Math.floor((column / width) ** 1.7 * usableBins);
      const end = Math.max(start + 1, Math.floor(((column + 1) / width) ** 1.7 * usableBins));
      let sum = 0;
      for (let index = start; index < end; index += 1) sum += frequencyData[index];
      const level = sum / Math.max(1, end - start) / 255;
      const threshold = row / height;
      if (level >= threshold) {
        const intensity = Math.min(charset.length - 1, Math.floor((level - threshold + .15) * charset.length));
        line += charset[Math.max(1, intensity)];
      } else if (Math.abs(level - threshold) < .025) {
        line += '.';
      } else {
        line += ' ';
      }
    }
    lines.push(line);
  }

  asciiScreen.textContent = lines.join('\n');
  animationFrame = requestAnimationFrame(renderSpectrum);
}

function startVisualizer() {
  ensureAudioGraph();
  cancelAnimationFrame(animationFrame);
  renderSpectrum();
  signalStatus.textContent = 'LIVE';
}

function stopDemo() {
  demoNodes.forEach((node) => {
    try { node.stop?.(); } catch (_) { /* already stopped */ }
    try { node.disconnect?.(); } catch (_) { /* already disconnected */ }
  });
  demoNodes = [];
}

function loadFile(file) {
  if (!file || !file.type.startsWith('audio/')) {
    signalStatus.textContent = 'INVALID FILE';
    return;
  }
  stopDemo();
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  audio.src = objectUrl;
  audio.load();
  loadedFile = true;
  playButton.disabled = false;
  playButton.textContent = 'Play';
  trackLabel.textContent = file.name.toUpperCase();
  signalStatus.textContent = 'READY';
}

fileInput.addEventListener('change', () => loadFile(fileInput.files[0]));

playButton.addEventListener('click', async () => {
  ensureAudioGraph();
  if (audio.paused) {
    stopDemo();
    await audio.play();
  } else {
    audio.pause();
  }
});

audio.addEventListener('play', () => {
  playButton.textContent = 'Pause';
  startVisualizer();
});

audio.addEventListener('pause', () => {
  playButton.textContent = 'Play';
  signalStatus.textContent = loadedFile ? 'PAUSED' : 'IDLE';
});

audio.addEventListener('ended', () => {
  playButton.textContent = 'Play';
  signalStatus.textContent = 'COMPLETE';
});

audio.addEventListener('loadedmetadata', () => {
  durationLabel.textContent = formatTime(audio.duration);
});

audio.addEventListener('timeupdate', () => {
  currentTimeLabel.textContent = formatTime(audio.currentTime);
  seek.value = audio.duration ? Math.round((audio.currentTime / audio.duration) * 1000) : 0;
});

seek.addEventListener('input', () => {
  if (audio.duration) audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
});

volume.addEventListener('input', () => {
  audio.volume = Number(volume.value);
});
audio.volume = Number(volume.value);

demoButton.addEventListener('click', async () => {
  ensureAudioGraph();
  audio.pause();
  stopDemo();
  const now = audioContext.currentTime;
  const master = audioContext.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.gain.exponentialRampToValueAtTime(0.09, now + 0.08);
  master.gain.exponentialRampToValueAtTime(0.0001, now + 8);
  master.connect(analyser);

  [110, 164.81, 220, 329.63].forEach((frequency, index) => {
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = index % 2 ? 'triangle' : 'sine';
    oscillator.frequency.setValueAtTime(frequency, now);
    oscillator.frequency.exponentialRampToValueAtTime(frequency * (1.5 + index * .1), now + 8);
    gain.gain.value = .24 / (index + 1);
    oscillator.connect(gain);
    gain.connect(master);
    oscillator.start(now + index * .04);
    oscillator.stop(now + 8);
    demoNodes.push(oscillator, gain);
  });

  demoNodes.push(master);
  trackLabel.textContent = 'SYNTHETIC SIGNAL DEMO';
  signalStatus.textContent = 'LIVE';
  startVisualizer();
  setTimeout(() => {
    if (!loadedFile) signalStatus.textContent = 'IDLE';
  }, 8100);
});

fullscreenButton.addEventListener('click', async () => {
  if (!document.fullscreenElement) await dropZone.requestFullscreen();
  else await document.exitFullscreen();
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
  });
});

dropZone.addEventListener('drop', (event) => loadFile(event.dataTransfer.files[0]));

document.addEventListener('keydown', (event) => {
  if (event.target.matches('input, button')) return;
  if (event.code === 'Space' && loadedFile) {
    event.preventDefault();
    playButton.click();
  }
});

document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    await navigator.clipboard.writeText(target.innerText);
    const original = button.textContent;
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = original; }, 1200);
  });
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js'));
}
