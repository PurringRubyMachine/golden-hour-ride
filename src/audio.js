// Wind and tyre sound from filtered noise.

/* ---------- sound: wind and tyres from filtered noise ---------- */
export let audio = null;
function startAudio() {
  if (audio) return;
  const ac = new AudioContext(), buf = ac.createBuffer(1, ac.sampleRate * 2, ac.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const mk = (type, freq, q) => {
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
    const f = ac.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    const g = ac.createGain(); g.gain.value = 0;
    src.connect(f).connect(g).connect(ac.destination); src.start();
    return { f, g };
  };
  audio = { ac, wind: mk('bandpass', 500, 0.5), tyre: mk('lowpass', 240, 0.8), rain: mk('highpass', 2600, 0.5) };
}
addEventListener('pointerdown', startAudio); addEventListener('keydown', startAudio);

