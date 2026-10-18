"""Builds the SD-card sound pack (sd-card/01..05/001-008.mp3) and the
simulator's ambience files (simulator/sounds/sim/*.mp3).

Sources (see sd-card/CREDITS.md):
  * Sonic Pi sample library, CC0 (recordings from freesound.org)
  * Freedoom sound effects, BSD 3-clause
  * Voice lines spoken by the Kokoro TTS model, Apache 2.0
  * Everything else (bells, plucks, organ, wind, boings) synthesised here

Run:  python tools/soundpack/build.py --sonicpi PATH --freedoom PATH --kokoro PATH
Needs numpy, soundfile, kokoro-onnx and ffmpeg (with rubberband) on PATH.
"""
import argparse
import os
import subprocess
import numpy as np

SR = 44100
RNG = np.random.default_rng(7)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = None   # parsed args
_tts = None


# ---------------------------------------------------------------- basics
def ffmpeg_decode(path, extra=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if extra:
        cmd += ["-af", extra]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, check=True, capture_output=True).stdout, np.float32).copy()


def ffmpeg_filter(x, af):
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    out = subprocess.run(cmd, input=x.astype(np.float32).tobytes(), check=True, capture_output=True).stdout
    return np.frombuffer(out, np.float32).copy()


def sp(name):
    return fade(ffmpeg_decode(os.path.join(A.sonicpi, name + ".flac")), 0.0, 0.01)


def fd(name):
    # Freedoom sounds are 8-bit 11-22 kHz; soften the aliasing a little
    return fade(ffmpeg_decode(os.path.join(A.freedoom, name + ".wav"), "highpass=f=40,lowpass=f=7000"), 0.002, 0.03)


def say(text, voice, speed=1.0, semis=0.0, lang="en-us", ph=False):
    """Speak text, or raw IPA when ph=True (for screams and laughs the
    phonemizer would otherwise spell out letter by letter)."""
    global _tts
    if _tts is None:
        from kokoro_onnx import Kokoro
        _tts = Kokoro(os.path.join(A.kokoro, "kokoro-v1.0.onnx"), os.path.join(A.kokoro, "voices-v1.0.bin"))
    s, sr = _tts.create(text, voice=voice, speed=speed, lang=lang, is_phonemes=ph)
    x = resample(np.asarray(s, np.float32), sr / SR)
    return fade(pitch(x, semis) if semis else x, 0.002, 0.03)


def resample(x, ratio):
    """ratio > 1 plays faster and higher (like a tape)."""
    n = int(len(x) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x).astype(np.float32)


def pitch(x, semis):
    """Pitch shift keeping the length (rubberband, formants follow)."""
    return ffmpeg_filter(x, "rubberband=pitch=%.5f:formant=preserved" % (2 ** (semis / 12)))


def chip(x, semis):
    """Tape-speed pitch shift: higher AND faster, like a cartoon critter."""
    return resample(x, 2 ** (semis / 12))


def t(sec):
    return np.arange(int(sec * SR)) / SR


def silence(sec):
    return np.zeros(int(sec * SR), np.float32)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.2):
    e = np.ones(n, np.float32) * s
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    ai = min(ai, n)
    e[:ai] = np.linspace(0, 1, ai)
    e[ai:ai + di] = np.linspace(1, s, len(e[ai:ai + di]))
    if ri and n > ri:
        e[-ri:] *= np.linspace(1, 0, ri)
    return e


def mix(*parts, length=None):
    """parts: (signal, start_seconds, gain)"""
    end = max(int(st * SR) + len(sig) for sig, st, g in parts)
    out = np.zeros(length or end, np.float32)
    for sig, st, g in parts:
        i = int(st * SR)
        if i >= len(out):
            continue
        seg = sig[: len(out) - i]
        out[i:i + len(seg)] += seg * g
    return out


def lowpass(x, f):
    return ffmpeg_filter(x, "lowpass=f=%d" % f)


def highpass(x, f):
    return ffmpeg_filter(x, "highpass=f=%d" % f)


def bandpass(x, f, w=1.0):
    return ffmpeg_filter(x, "bandpass=f=%d:width_type=o:w=%.2f" % (f, w))


def reverb(x, size=1.6, wet=0.3, tone=5000):
    n = int(size * SR)
    ir = RNG.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / SR * 6.9 / size)
    ir = lowpass(ir, tone)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    m = len(x) + n
    nfft = 1 << (m - 1).bit_length()
    w = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:m].astype(np.float32)
    dry = np.concatenate([x, np.zeros(n, np.float32)])
    return dry * (1 - wet * 0.5) + w * wet


def fade(x, fin=0.005, fout=0.05):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def trim(x, thresh=0.003):
    idx = np.where(np.abs(x) > thresh)[0]
    if not len(idx):
        return x
    return x[max(0, idx[0] - 200): idx[-1] + 2000]


def cut(x, sec):
    return fade(x[: int(sec * SR)], 0.002, min(0.3, sec / 4))


def loop_to(x, sec):
    """Repeat x with a short crossfade at every seam."""
    n, xf = int(sec * SR), int(0.5 * SR)
    out = x.copy()
    ramp = np.linspace(0, 1, xf, dtype=np.float32)
    while len(out) < n:
        out = np.concatenate([out[:-xf], out[-xf:] * (1 - ramp) + x[:xf] * ramp, x[xf:]])
    return out[:n]


# ---------------------------------------------------------------- instruments
def ks_pluck(freq, dur, bright=0.5, decay=0.996):
    """Karplus-Strong plucked string, vectorised one period at a time."""
    N = max(2, int(SR / freq))
    n = int(dur * SR)
    out = np.zeros(n + N + 1, np.float32)
    burst = RNG.uniform(-1, 1, N).astype(np.float32)
    burst = burst * bright + np.convolve(burst, np.ones(4) / 4, "same") * (1 - bright)
    out[:N] = burst
    pos = N
    while pos < n + 1:
        prev = out[pos - N: pos + 1 - 0]          # N+1 samples
        blk = 0.5 * (prev[:-1] + prev[1:]) * decay
        k = min(N, len(out) - pos)
        out[pos:pos + k] = blk[:k]
        pos += k
    return fade(out[:n], 0.001, 0.03)


def bell(freq, dur=2.5, gain=1.0):
    tt = t(dur)
    ratios = [0.56, 0.92, 1.19, 1.71, 2.0, 2.74, 3.0, 3.76, 4.07]
    amps = [1, 0.67, 1, 1.8, 2.67, 1.67, 1.46, 1.33, 1.33]
    durs = [1, 0.9, 0.65, 0.55, 0.325, 0.35, 0.25, 0.2, 0.15]
    y = np.zeros_like(tt)
    for r, a, d in zip(ratios, amps, durs):
        y += a * np.sin(2 * np.pi * freq * r * tt + RNG.uniform(0, 6)) * np.exp(-tt / (d * dur * 0.35))
    return fade((y / 8 * gain).astype(np.float32), 0.001, 0.05)


def organ(freq, dur):
    tt = t(dur)
    drawbars = [(0.5, 0.6), (1, 1.0), (2, 0.7), (3, 0.45), (4, 0.35), (6, 0.2), (8, 0.25)]
    y = np.zeros_like(tt)
    for h, a in drawbars:
        y += a * np.sin(2 * np.pi * freq * h * tt * (1 + 0.002 * np.sin(2 * np.pi * 6.3 * tt)))
    y *= 1 + 0.25 * np.sin(2 * np.pi * 6.3 * tt)      # leslie wobble
    return (y / 3.5 * env_adsr(len(tt), 0.01, 0.05, 0.9, 0.06)).astype(np.float32)


def bass(freq, dur):
    tt = t(dur)
    saw = 2 * ((freq * tt) % 1) - 1
    y = 0.6 * np.sin(2 * np.pi * freq * tt) + 0.4 * saw
    return (y * env_adsr(len(tt), 0.004, 0.12, 0.55, 0.05)).astype(np.float32)


def piano(freq, dur):
    # a bright pluck with a sine body reads as an upright piano in a mix
    a = ks_pluck(freq, dur + 0.3, bright=0.9, decay=0.998)
    tt = t(dur + 0.3)
    body = np.sin(2 * np.pi * freq * tt) * np.exp(-tt * 3)
    y = 0.7 * a + 0.3 * body
    return fade(y.astype(np.float32), 0.001, 0.12)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def jingle(dur=0.25, hits=24, bright=1.0):
    """A shake of sleigh bells: lots of tiny detuned metallic pings."""
    out = silence(dur + 0.4)
    for _ in range(hits):
        st = abs(RNG.normal(0.03, dur / 3))
        f = RNG.uniform(2600, 5200) * bright
        tt = t(0.25)
        ping = sum(np.sin(2 * np.pi * f * r * tt) * np.exp(-tt * (35 + 20 * r)) for r in (1, 1.49, 2.13))
        i = int(st * SR)
        if i + len(ping) < len(out):
            out[i:i + len(ping)] += ping * RNG.uniform(0.2, 1) / 3
    return highpass(out, 1800)


def noise(sec):
    return RNG.standard_normal(int(sec * SR)).astype(np.float32)


def wind(sec, base=500, howl=True):
    n = noise(sec)
    tt = t(sec)
    out = np.zeros_like(n)
    # three band-passed layers whose loudness drifts slowly like gusts
    for i, f in enumerate([base * 0.5, base, base * 2.2]):
        b = bandpass(n, f, 1.2)
        g = 0.5 + 0.5 * np.sin(2 * np.pi * (0.13 + 0.07 * i) * tt + i * 2)
        out += b * g ** 2
    if howl:
        f0 = base * 1.4 * (1 + 0.35 * np.sin(2 * np.pi * 0.18 * tt) + 0.1 * np.sin(2 * np.pi * 0.71 * tt))
        ph = 2 * np.pi * np.cumsum(f0) / SR
        out += 0.12 * np.sin(ph) * (0.4 + 0.6 * np.sin(2 * np.pi * 0.2 * tt) ** 2)
    return fade(out.astype(np.float32), 0.6, 1.2)


def boing(sec=1.1, f0=180):
    tt = t(sec)
    f = f0 * (1 + 0.55 * np.exp(-tt * 3) * np.sin(2 * np.pi * 11 * tt)) * (1 + 0.6 * np.exp(-tt * 6))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3.01 * ph)
    y = y * np.exp(-tt * 2.6)
    thump = sp("drum_tom_lo_hard")
    return fade(mix((fade(y.astype(np.float32), 0.001, 0.15), 0, 1), (thump, 0, 0.12)), 0.001, 0.1)


def creak(sec=2.5, f0=90, rough=0.5):
    """Stick-slip creak: a train of tiny clicks whose rate wanders."""
    tt = t(sec)
    rate = f0 * (1 + 0.6 * np.sin(2 * np.pi * 0.45 * tt + 1) + 0.25 * np.sin(2 * np.pi * 1.7 * tt))
    ph = np.cumsum(rate) / SR
    clicks = np.diff(np.floor(ph), prepend=0).astype(np.float32)
    clicks *= RNG.uniform(1 - rough, 1, len(clicks))
    body = bandpass(clicks, 700, 1.5) * 3 + bandpass(clicks, 1600, 1.0) * 1.5 + bandpass(clicks, 2900, 0.8)
    swell = np.sin(np.pi * np.clip(tt / sec, 0, 1)) ** 0.7
    return fade((body * swell).astype(np.float32), 0.05, 0.2)


def heartbeat(sec=6.0, bpm=78):
    kick = lowpass(sp("drum_heavy_kick"), 180)
    beat = 60 / bpm
    parts = []
    k = 0
    while k * beat < sec - 0.5:
        st = k * beat
        parts += [(kick, st, 1.0), (kick, st + 0.22, 0.7)]
        k += 1
        bpm *= 1.03       # speeds up as the guest panics
        beat = 60 / bpm
    return mix(*parts)


def ticking(sec=6.0):
    tick = highpass(sp("perc_snap"), 1500)
    tock = lowpass(sp("perc_snap"), 2500)
    return mix(*[(tick if i % 2 == 0 else tock, i * 0.5, 0.8) for i in range(int(sec * 2))],
               (bell(midi(84), 2.0), sec - 0.8, 0.6), (bell(midi(79), 2.0), sec - 0.4, 0.6))


def chatter(sec=1.5, rate=22, f=2500):
    """Squirrel chatter: fast raspy chirps."""
    out = silence(sec)
    i = 0.0
    while i < sec - 0.08:
        tt = t(0.04)
        ff = f * RNG.uniform(0.85, 1.15) * (1 - tt * 4)
        ph = 2 * np.pi * np.cumsum(ff) / SR
        chirp = (np.sin(ph) + 0.4 * np.sign(np.sin(ph))) * np.sin(np.pi * tt / 0.04)
        j = int(i * SR)
        out[j:j + len(chirp)] += chirp * RNG.uniform(0.5, 1)
        i += 1 / rate * RNG.uniform(0.7, 1.4)
        if RNG.random() < 0.12:
            i += 0.12
    return bandpass(out, 2600, 2)


def teeth(sec=1.2, rate=16):
    clack = highpass(sp("elec_tick"), 1200)
    return mix(*[(clack, i / rate + RNG.uniform(0, 0.01), RNG.uniform(0.6, 1)) for i in range(int(sec * rate))])


def ice_crack(sec=2.2):
    out = silence(sec)
    snap = sp("perc_snap2")
    for _ in range(40):
        st = abs(RNG.normal(0.15, 0.35))
        burst = highpass(noise(0.01), 2000) * np.exp(-t(0.01) * 400)
        i = int(st * SR)
        if i < len(out) - 500:
            out[i:i + len(burst)] += burst * RNG.uniform(0.2, 1)
    boom = cut(lowpass(sp("misc_cineboom"), 900), 1.8)
    return reverb(mix((out, 0, 1), (snap, 0.05, 1), (chip(snap, -7), 0.32, 1.0), (boom, 0.05, 0.6)), 1.2, 0.35)


def crunch(sec=1.6):
    out = silence(sec)
    for bite in (0.0, 0.55, 1.05):
        for _ in range(26):
            st = bite + abs(RNG.normal(0, 0.06))
            dur = RNG.uniform(0.003, 0.02)
            b = bandpass(noise(dur), RNG.uniform(1500, 4500), 1.0) * np.exp(-t(dur) * 200)
            i = int(st * SR)
            if i + len(b) < len(out):
                out[i:i + len(b)] += b * RNG.uniform(0.3, 1.2)
    return out


def honk(sec=0.5, f=420):
    """Clown bicycle horn: a reedy, slightly bending square into a bulb."""
    tt = t(sec)
    ff = f * (1 + 0.04 * np.sin(2 * np.pi * 6 * tt)) * (1 - 0.06 * tt / sec)
    ph = 2 * np.pi * np.cumsum(ff) / SR
    y = np.tanh(4 * np.sin(ph)) + 0.5 * np.sin(2 * ph)
    y = bandpass(y.astype(np.float32), 1100, 2.5) * env_adsr(len(tt), 0.01, 0.05, 0.85, 0.08)
    return y


EVIL = "mwˈɑː hˈɑː hˈɑː hˈɑː hˈɑː hˈɑː hˈɑːːːː!"


# ---------------------------------------------------------------- music
class Song:
    def __init__(self, bpm, bars, swing=0.0):
        self.bpm, self.swing = bpm, swing
        self.beat = 60 / bpm
        self.len = bars * 4 * self.beat
        self.parts = []

    def at(self, beat):
        whole, frac = divmod(beat, 1)
        if self.swing and abs(frac - 0.5) < 1e-6:
            frac += self.swing
        return (whole + frac) * self.beat

    def add(self, sig, beat, gain=1.0):
        self.parts.append((sig, self.at(beat), gain))

    def melody(self, inst, notes, start=0, gain=1.0, octave=0):
        b = start
        for n, d in notes:
            if n is not None:
                self.add(inst(midi(n + 12 * octave), d * self.beat * 0.95), b, gain)
            b += d
        return b

    def drums(self, pattern, kick, snare, hat, start=0, bars=None, gain=1.0):
        """pattern: 16-char strings per instrument for one bar (K, S, H)."""
        bars = bars or int(self.len / (4 * self.beat))
        for bar in range(bars):
            for i in range(16):
                b = start + bar * 4 + i / 4
                if pattern["K"][i] != ".":
                    self.add(kick, b, gain)
                if pattern["S"][i] != ".":
                    self.add(snare, b, gain * (0.9 if pattern["S"][i] == "x" else 0.4))
                if pattern["H"][i] != ".":
                    self.add(hat, b, gain * (0.5 if pattern["H"][i] == "x" else 0.25))

    def render(self):
        return mix(*self.parts, length=int((self.len + 2.0) * SR))


DISCO = {"K": "x...x...x...x...", "S": "....x.......x...", "H": "..x...x...x...x."}
ROCK = {"K": "x.....x.x.......", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x."}
HOP = {"K": "x.......x.x.....", "S": "....x.......x..o", "H": "x.xxx.xxx.xxx.xx"}
SHUFFLE = {"K": "x.......x.......", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x."}
BOOGIE = {"K": "x.......x.......", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x."}


def kit():
    return sp("bd_haus"), sp("sn_dolf"), sp("drum_cymbal_closed")


def spider_disco():
    s = Song(118, 18)
    k, sn, h = kit()
    s.drums(DISCO, k, sn, h, start=4, bars=16)
    # octave disco bass on D
    for bar in range(16):
        root = [50, 50, 46, 45][bar // 2 % 4]
        for i in range(8):
            s.add(bass(midi(root + (12 if i % 2 else 0) - 12), s.beat * 0.45), 4 + bar * 4 + i / 2, 0.55)
    toccata = [(81, .25), (79, .25), (81, 2.5), (None, 1), (79, .25), (77, .25), (76, .25), (74, .25),
               (73, .75), (74, 2.25), (None, 4)]
    low = [(69, .25), (67, .25), (69, 2.5), (None, 1), (64, .5), (65, .5), (61, .75), (62, 2.25), (None, 4)]
    s.melody(organ, toccata, start=0, gain=0.55, octave=-1)
    s.melody(organ, toccata, start=20, gain=0.5, octave=-1)
    s.melody(organ, low, start=36, gain=0.5)
    s.melody(organ, toccata, start=52, gain=0.5, octave=-1)
    # stabs
    for bar in (10, 11, 14, 15):
        for c in (62, 65, 69):
            s.add(organ(midi(c), s.beat * 0.4), 4 + bar * 4 + 1.5, 0.25)
    laugh = reverb(say(EVIL, "bm_george", 0.85, -4, ph=True), 1.5, 0.35)
    s.parts.append((laugh, s.at(68), 1.0))
    return s.render()


def jingle_bells_rock():
    s = Song(150, 18)
    k, sn, h = kit()
    s.drums(ROCK, k, sn, h, start=4, bars=16)
    q = 1
    verse = [(64, q), (64, q), (64, 2), (64, q), (64, q), (64, 2), (64, q), (67, q), (60, 1.5), (62, .5), (64, 4),
             (65, q), (65, q), (65, 1.5), (65, .5), (65, q), (64, q), (64, q), (64, .5), (64, .5),
             (64, q), (62, q), (62, q), (64, q), (62, 2), (67, 2)]
    verse2 = verse[:20] + [(67, q), (67, q), (65, q), (62, q), (60, 4)]
    end = s.melody(lambda f, d: bell(f, 1.6), [(n, d) for n, d in verse], start=4, gain=0.6, octave=1)
    s.melody(lambda f, d: bell(f, 1.6), verse2, start=end, gain=0.6, octave=1)
    s.melody(piano, verse + verse2, start=4, gain=0.3)
    chords = [48, 48, 48, 48, 53, 48, 50, 43, 48, 48, 48, 48, 53, 48, 43, 48]
    for bar, r in enumerate(chords):
        for i in range(4):
            s.add(bass(midi(r + (7 if i % 2 else 0) - 12), s.beat * 0.8), 4 + bar * 4 + i, 0.5)
    for b in range(4, 68, 1):
        s.add(jingle(0.12, 10), b + 0.5, 0.35)
    s.add(reverb(say("Ho ho ho! Merry Christmas!", "am_santa", 0.85, -2), 1.0, 0.25), 68, 1.0)
    return s.render()


def hop_hop_hooray():
    s = Song(132, 17)
    k, sn, h = kit()
    s.drums(HOP, k, sn, h, start=4, bars=16, gain=0.85)
    a = [(72, .5), (76, .5), (79, 1), (76, .5), (79, .5), (84, 2), (81, .5), (79, .5), (77, .5), (76, .5),
         (74, 1), (79, 1), (72, .5), (76, .5), (79, 1), (81, .5), (79, .5), (77, 1), (76, .5), (74, .5),
         (72, 2), (None, 2)]
    b = [(77, .5), (77, .5), (81, 1), (79, .5), (77, .5), (76, 1), (74, .5), (76, .5), (77, .5), (79, .5),
         (81, 2), (79, .5), (79, .5), (84, 1), (83, .5), (81, .5), (79, 1), (77, .5), (76, .5), (74, .5),
         (72, 2.5)]
    x = s.melody(lambda f, d: ks_pluck(f, d + 0.4, 0.8, 0.995), a, start=4, gain=0.7)
    x = s.melody(lambda f, d: ks_pluck(f, d + 0.4, 0.8, 0.995), b, start=x, gain=0.7)
    x = s.melody(lambda f, d: bell(f * 2, 1.0), a, start=x, gain=0.35)
    s.melody(lambda f, d: ks_pluck(f, d + 0.4, 0.8, 0.995), b, start=x, gain=0.7)
    for bar in range(16):
        r = [48, 53, 55, 48][bar % 4]
        for i in (0, 1.5, 2, 3.5):
            s.add(bass(midi(r - 12), s.beat * 0.4), 4 + bar * 4 + i, 0.5)
    for bar in range(16):
        s.add(boing(0.5, 300), 4 + bar * 4 + 3.5, 0.12)
    s.add(chip(say("Happy Easter!", "af_sky", 1.05), 4), 68, 1.0)
    return s.render()


def nutty_shuffle():
    s = Song(124, 18, swing=0.17)
    k, sn, h = kit()
    s.drums(SHUFFLE, k, sn, sp("hat_cab"), start=4, bars=16, gain=0.8)
    prog = [(55, [55, 59, 62]), (55, [55, 59, 62]), (60, [60, 64, 67]), (55, [55, 59, 62]),
            (62, [62, 66, 69]), (60, [60, 64, 67]), (55, [55, 59, 62]), (62, [62, 66, 69])] * 2
    for bar, (r, ch) in enumerate(prog):
        roll = [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1], ch[0] + 12, ch[2]]
        for i, n in enumerate(roll):
            s.add(ks_pluck(midi(n), 0.5, 0.95, 0.993), 4 + bar * 4 + i / 2, 0.45)
        s.add(bass(midi(r - 24), s.beat * 0.9), 4 + bar * 4, 0.55)
        s.add(bass(midi(r - 17), s.beat * 0.9), 4 + bar * 4 + 2, 0.5)
    for b in (20, 36, 52, 66):
        s.add(chatter(0.6), b, 0.35)
    s.add(chip(say("Mine! All mine!", "am_puck", 1.0), 5), 68, 1.0)
    return s.render()


def blizzard_boogie():
    s = Song(128, 17, swing=0.15)
    k, sn, h = kit()
    s.drums(BOOGIE, k, sn, h, start=4, bars=12, gain=0.8)
    blues = [48, 48, 48, 48, 53, 53, 48, 48, 55, 53, 48, 55]
    walk = [0, 4, 7, 9, 10, 9, 7, 4]
    for bar, r in enumerate(blues):
        for i, o in enumerate(walk):
            s.add(piano(midi(r - 12 + o), s.beat * 0.45), 4 + bar * 4 + i / 2, 0.55)
        for c in ((r + 16, r + 19, r + 22) if bar % 2 == 0 else (r + 15, r + 19, r + 22)):
            s.add(piano(midi(c), s.beat * 0.3), 4 + bar * 4 + 1.5, 0.2)
            s.add(piano(midi(c), s.beat * 0.3), 4 + bar * 4 + 3.5, 0.18)
    s.add(wind(8, 450), 0, 0.6)
    s.add(wind(10, 500), 50, 0.6)
    for bar in (52, 56, 60):
        s.add(teeth(0.6), bar, 0.5)
    s.add(reverb(pitch(say("bɹˈʌːɹɹɹ! snˈoʊ dˈeɪ!", "am_fenrir", 0.9, ph=True), -5), 1.4, 0.3), 54, 1.0)
    return s.render()


# ---------------------------------------------------------------- the pack
def pack():
    P = {}
    # 01 Halloween: Corner Spider
    P["01"] = {
        1: mix((bandpass(noise(1.8), 5500, 1.4) * np.sin(np.pi * t(1.8) / 1.8) ** 0.5, 0, 0.6),
               (bandpass(noise(1.8), 3000, 0.8) * np.sin(np.pi * t(1.8) / 1.8) ** 2, 0, 0.25),
               (chip(fd("dsbspact"), -3), 1.0, 0.5)),
        2: reverb(mix((fd("dspdiehi"), 0, 0.9), (say("ˈɑːːːːːːːːː!", "af_bella", 0.8, ph=True), 0.05, 0.8),
                      (fd("dsbgdth1"), 0.45, 0.6), (chip(fd("dsspisit"), -2), 0.0, 0.5)), 1.4, 0.3),
        3: reverb(say(EVIL, "bm_george", 0.8, -4, ph=True), 1.6, 0.35),
        4: reverb(mix((creak(2.6, 70), 0, 1), (sp("perc_door"), 0.3, 0.6)), 0.9, 0.2),
        5: heartbeat(6.5),
        6: boing(),
        7: spider_disco(),
        8: reverb(mix((chip(say("hˈaɪːːːː!", "af_nicole", 0.9, ph=True), 3), 0, 1), (sp("ambi_dark_woosh"), 0.4, 0.4)), 1.2, 0.3),
    }
    # 02 Christmas: Rappelling Santa
    P["02"] = {
        1: reverb(say("Humph. Grumble grumble. Too many cookies!", "am_santa", 0.95, -2), 0.7, 0.18),
        2: reverb(mix((say("HO! HO! HO!", "am_santa", 0.75, -3), 0, 1), (jingle(0.6, 60), 0.1, 0.4)), 1.3, 0.25),
        3: reverb(say("Ha ha ha ha! Ho ho ho ho!", "am_santa", 0.95, -2), 1.0, 0.22),
        4: reverb(mix((creak(2.2, 55, 0.7), 0, 1), (lowpass(sp("perc_impact1"), 1500), 1.8, 0.5)), 1.6, 0.3),
        5: mix(*[(jingle(0.18, 18), i * 0.42, 0.9) for i in range(14)], (jingle(0.8, 80), 5.9, 0.9)),
        6: boing(1.1, 160),
        7: jingle_bells_rock(),
        8: reverb(say("Have you been naughty... or nice?", "am_santa", 0.9, -2), 1.2, 0.25),
    }
    # 03 Easter: Bungee Bunny
    P["03"] = {
        1: mix((crunch(1.7), 0, 1), (chip(say("nom nom nom!", "af_sky", 1.1), 5), 1.6, 0.9)),
        2: mix((honk(0.35), 0, 1), (honk(0.5, 400), 0.45, 1)),
        3: chip(say("Hee hee hee hee hee!", "af_sky", 1.0), 5),
        4: mix((boing(0.9, 420), 0, 1), (boing(0.7, 600), 0.25, 0.5)),
        5: ticking(6.0),
        6: boing(1.1, 200),
        7: hop_hop_hooray(),
        8: reverb(mix((chip(say("Happy Easter!", "af_sky", 1.0), 4), 0, 1), (bell(midi(88), 1.5), 0.9, 0.3)), 0.8, 0.2),
    }
    # 04 Fall: Acorn Heist Squirrel
    P["04"] = {
        1: mix((chatter(1.6), 0, 1), (chip(say("Hey! Hey! Hey!", "am_puck", 1.2), 6), 1.0, 0.9)),
        2: mix((chip(say("ˈiːːːːːːk!", "af_jessica", 0.8, ph=True), 6), 0, 1), (chatter(0.5, 30, 3200), 0.7, 0.5)),
        3: chip(say("Heh heh heh heh!", "am_puck", 1.0), 6),
        4: reverb(mix((creak(2.4, 120, 0.6), 0, 1), (lowpass(sp("perc_snap2"), 3000), 2.2, 0.6)), 1.0, 0.25),
        5: mix((wind(6.0, 650, False), 0, 1), (sp("misc_crow"), 1.5, 0.6), (sp("misc_crow"), 2.2, 0.5)),
        6: boing(1.0, 220),
        7: nutty_shuffle(),
        8: chip(say("Mine! All mine!", "am_puck", 1.0), 5),
    }
    # 05 Winter: Brain Freeze Yeti
    P["05"] = {
        1: mix((teeth(1.6), 0, 0.8), (pitch(say("Ooh, so cold.", "am_fenrir", 0.9), -3), 0.3, 0.9)),
        2: reverb(mix((pitch(say("ɹˈɑːːːːːːɹ!", "am_onyx", 0.7, ph=True), -9), 0, 1),
                      (chip(fd("dsdmact"), -5), 0.05, 0.8), (cut(lowpass(sp("misc_cineboom"), 300), 2.5), 0, 0.6)),
                  2.0, 0.35),
        3: reverb(pitch(say("Ho ho! Hah hah hah hah!", "am_fenrir", 0.85), -6), 1.6, 0.3),
        4: ice_crack(),
        5: wind(6.5, 420, True),
        6: boing(1.1, 150),
        7: blizzard_boogie(),
        8: reverb(pitch(say("bɹˈʌːːɹɹɹ! sˌoʊ kˈoʊld!", "am_fenrir", 0.85, ph=True), -5), 1.4, 0.3),
    }
    return P


def extras():
    """Ambience the simulator layers under the scene."""
    thunder_src = lowpass(sp("misc_cineboom"), 1200)
    rumble = lowpass(noise(5), 180) * np.exp(-t(5) * 0.9) * 3
    E = {
        "thunder": reverb(mix((thunder_src, 0, 1), (rumble, 0.1, 1)), 2.5, 0.4),
        "amb-halloween": mix((loop_to(sp("ambi_haunted_hum"), 20), 0, 0.8), (wind(20, 380, True), 0, 0.25),
                             (sp("misc_crow"), 6, 0.5), (sp("misc_crow"), 14.5, 0.4)),
        "amb-christmas": mix((wind(20, 300, False), 0, 0.25), *[(jingle(0.3, 20, 0.9), 3 + i * 5.3, 0.06) for i in range(3)]),
        "amb-easter": mix(*[(chip(sp("misc_crow"), 14), 1 + i * 1.9, 0.15) for i in range(10)],
                          (wind(20, 900, False), 0, 0.08), length=20 * SR),
        "amb-fall": mix((wind(20, 650, False), 0, 0.6), (sp("misc_crow"), 4, 0.5), (sp("misc_crow"), 4.6, 0.4),
                        (sp("misc_crow"), 13, 0.5)),
        "amb-winter": mix((wind(20, 420, True), 0, 0.7)),
        "door": mix((creak(1.3, 140, 0.4), 0, 0.7), (lowpass(sp("perc_impact1"), 1200), 1.25, 0.4)),
        "footsteps": mix(*[(lowpass(sp("drum_tom_lo_soft"), 600), i * 0.48, 0.5 + 0.1 * (i % 2)) for i in range(6)]),
        "gasp": say("Ah!", "af_heart", 1.0),
        "gasp2": say("Whoa!", "am_michael", 1.0),
        "laugh-guest": say("Ha ha ha ha!", "af_heart", 1.0),
        "laugh-guest2": say("Ha ha ha!", "am_adam", 1.0),
        "zap": reverb(mix((highpass(noise(0.4), 2000) * np.exp(-t(0.4) * 10), 0, 0.5)), 0.6, 0.3),
    }
    return E


# ---------------------------------------------------------------- the other props
def thunder_roll(sec, rolls, crack=0.0, bright=900):
    """Rolling thunder: low noise shaped by a handful of decaying 'rolls',
    optionally led by a sharp crack (close strikes)."""
    base = lowpass(noise(sec), bright) * 2.5 + lowpass(noise(sec), 120) * 3
    tt = t(sec)
    env = np.zeros_like(tt)
    for i in range(rolls):
        st = (i / rolls) * sec * 0.55 + RNG.uniform(0, 0.4)
        a = RNG.uniform(0.4, 1.0) * (1 - 0.5 * i / rolls)
        env += a * np.clip((tt - st) / 0.15, 0, 1) * np.exp(-np.clip(tt - st, 0, None) * RNG.uniform(0.8, 1.6))
    out = base * env
    parts = [(out, 0, 1.0), (cut(lowpass(sp("misc_cineboom"), 500), min(sec, 7)), 0.05, 0.5 + crack * 0.3)]
    if crack:
        crk = highpass(noise(0.08), 1500) * np.exp(-t(0.08) * 45) * 4
        rip = silence(0.6)
        for _ in range(60):                       # the tearing sound of a close bolt
            i = int(abs(RNG.normal(0.12, 0.12)) * SR)
            b = highpass(noise(0.004), 2500) * RNG.uniform(0.3, 1.5)
            if i + len(b) < len(rip):
                rip[i:i + len(b)] += b
        parts += [(crk, 0, crack), (rip, 0.0, crack * 0.8)]
    return reverb(fade(mix(*parts), 0.002, 1.0), 2.5, 0.35)


def bubbles(sec, rate=7, big=1.0):
    """Cauldron bubbles: each pop is a short rising tone (that's how real
    bubbles sound), plus a low gurgle underneath."""
    out = silence(sec)
    n = int(sec * rate)
    for _ in range(n):
        d = RNG.uniform(0.04, 0.12) * big
        st = RNG.uniform(0, sec - d - 0.01)
        f0 = RNG.uniform(250, 900) / big
        tt = t(d)
        f = f0 * (1 + tt / d * RNG.uniform(0.6, 1.4))
        ph = 2 * np.pi * np.cumsum(f) / SR
        pop = np.sin(ph) * np.exp(-tt / d * 4) * np.sin(np.pi * np.minimum(1, tt / 0.004))
        i = int(st * SR)
        out[i:i + len(pop)] += pop * RNG.uniform(0.3, 1.0)
    gurgle = lowpass(noise(sec), 180) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t(sec))) * 1.5
    return mix((out, 0, 1.6), (gurgle, 0, 0.2 * big))


def seamless(x, xf=1.0):
    """Crossfade the end into the start so the DFPlayer can loop it."""
    k = int(xf * SR)
    ramp = np.linspace(0, 1, k, dtype=np.float32)
    head = x[:k] * ramp + x[-k:] * (1 - ramp)
    return np.concatenate([head, x[k:-k]])


def squeak(f=4200, d=0.09, bend=0.25):
    tt = t(d)
    ff = f * (1 + bend * np.sin(np.pi * tt / d)) * (1 + 0.03 * np.sin(2 * np.pi * 60 * tt))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    y = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.sin(np.pi * tt / d) ** 0.7
    return y.astype(np.float32)


def squeaks(n=3, gap=0.13):
    return mix(*[(squeak(RNG.uniform(3600, 5200), RNG.uniform(0.05, 0.12), RNG.uniform(0.1, 0.4)), i * gap + RNG.uniform(0, 0.03), RNG.uniform(0.6, 1)) for i in range(n)])


def claws(sec=2.0, rate=28):
    out = silence(sec)
    tick = highpass(sp("elec_tick"), 2500)
    i = 0.0
    while i < sec - 0.05:
        j = int(i * SR)
        k = tick * RNG.uniform(0.2, 1)
        out[j:j + len(k)] += k[: len(out) - j]
        i += 1 / rate * RNG.uniform(0.5, 1.5)
    return bandpass(out, 4000, 2)


def props_pack():
    global RNG
    RNG = np.random.default_rng(11)          # props sound the same however the build is run
    wet = lambda x, s=1.2, w=0.3: reverb(x, s, w)
    announcer = lambda txt, sp_=1.0: wet(say(txt, "am_michael", sp_), 0.8, 0.15)
    crone = lambda txt, sp_=0.85: wet(ffmpeg_filter(pitch(say(txt, "bf_alice", sp_), -3), "vibrato=f=6:d=0.15"), 1.6, 0.3)
    cackle_ph = "hˈɛ hˈɛ hˈɛ hˈɛ hˈɛ hˈɛːː!"
    P = {}
    P["lightning"] = {
        1: thunder_roll(6.0, 4, crack=1.0, bright=1400),
        2: thunder_roll(5.5, 3, crack=0.9, bright=1200),
        3: thunder_roll(7.0, 5, crack=1.1, bright=1600),
        4: thunder_roll(8.0, 6, bright=500),
        5: thunder_roll(7.0, 5, bright=420),
        6: thunder_roll(9.0, 7, bright=360),
    }
    count = mix((announcer("Three!"), 0.0, 1), (announcer("Two!"), 1.0, 1), (announcer("One!"), 2.0, 1),
                (announcer("SCREAM!", 0.9), 2.95, 1.2),
                *[(lowpass(sp("drum_heavy_kick"), 300), b, 0.8) for b in (0, 1, 2)],
                (cut(sp("drum_cymbal_hard"), 1.5), 2.95, 0.5))
    fanfare = mix(*[(bell(midi(n), 1.6), i * 0.13, 0.7) for i, n in enumerate((72, 76, 79, 84))],
                  (bell(midi(88), 2.5), 0.55, 0.9), (announcer("New high score!", 0.95), 0.9, 1.1))
    P["screamometer"] = {
        1: count,
        2: fanfare,
        3: announcer("Is that all you've got? My grandma screams louder than that!"),
        4: announcer("Not bad. Not bad at all!"),
        5: mix((announcer("Whoa! My ears! My poor ears!", 1.05), 0, 1), (cut(sp("drum_cymbal_hard"), 1.2), 0, 0.4)),
        6: wet(pitch(say("Uh oh. You woke something up...", "bm_george", 0.85), -3), 2.0, 0.4),
    }
    P["cauldron"] = {
        1: seamless(bubbles(13.0, 11)),
        2: mix((crone("Who disturbs my stew?"), 0.2, 1), (cut(lowpass(chip(fd("dsdmact"), -6), 900), 2.0), 0, 0.5)),
        3: wet(ffmpeg_filter(chip(say(cackle_ph, "af_bella", 1.0, ph=True), 2), "vibrato=f=7:d=0.3"), 1.6, 0.35),
        4: crone("Mmm. You'll make a lovely soup!"),
        5: crone("Double, double, toil and trouble. Fire burn, and cauldron bubble!", 0.8),
        6: mix((bubbles(3.0, 14, big=2.2), 0, 1), (cut(lowpass(sp("misc_cineboom"), 700), 2.5), 0, 0.5)),
    }
    P["rat"] = {
        1: squeaks(3),
        2: mix((claws(2.2), 0, 1), (squeaks(2, 0.5), 0.8, 0.5)),
        3: mix((chip(say("ˈiːːːːk!", "af_jessica", 0.8, ph=True), 12), 0, 1), (squeaks(4, 0.08), 0.1, 0.6)),
        4: mix((bandpass(noise(0.9), 5000, 1.5) * np.sin(np.pi * t(0.9) / 0.9) ** 0.5, 0, 0.8), (squeak(3000, 0.15, -0.3), 0.85, 0.7)),
        5: chip(say("Eek! Eek!", "am_puck", 1.1), 10),
        6: mix(*[(squeaks(3, 0.11), RNG.uniform(0, 4), RNG.uniform(0.3, 0.9)) for _ in range(14)],
               (claws(5.0, 60), 0, 1), length=5 * SR),
    }
    return P


def normalise(x, target_rms_db=-16.0, peak=0.89):
    x = trim(x.astype(np.float64))
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * (10 ** (target_rms_db / 20) / rms)
    x = np.tanh(x / peak) * peak            # soft limiter
    return fade(x.astype(np.float32), 0.003, 0.04)


def write_mp3(x, path, lead=0.1, kbps=96):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.concatenate([silence(lead), x])
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-codec:a", "libmp3lame", "-b:a", "%dk" % kbps, "-ar", str(SR), path]
    subprocess.run(cmd, input=x.astype(np.float32).tobytes(), check=True)


def main():
    global A
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonicpi", required=True, help="sonic-pi/etc/samples")
    ap.add_argument("--freedoom", required=True, help="freedoom/sounds")
    ap.add_argument("--kokoro", required=True, help="folder with kokoro-v1.0.onnx and voices-v1.0.bin")
    ap.add_argument("--only", help="e.g. 01 or 01/7 or extras or props")
    A = ap.parse_args()
    if not A.only or A.only not in ("extras", "props"):
        for folder, slots in pack().items():
            for slot, sig in slots.items():
                key = "%s/%d" % (folder, slot)
                if A.only and not (A.only == folder or A.only == key):
                    continue
                kbps = 96 if slot == 7 else 128
                write_mp3(normalise(sig, -17 if slot == 7 else -16), os.path.join(ROOT, "sd-card", folder, "%03d.mp3" % slot), kbps=kbps)
                print("wrote", key)
    if not A.only or A.only == "extras":
        for name, sig in extras().items():
            write_mp3(normalise(sig, -20 if name.startswith("amb") else -16),
                      os.path.join(ROOT, "simulator", "sounds", "sim", name + ".mp3"), lead=0.0, kbps=64)
            print("wrote", name)
    if not A.only or A.only == "props":
        # every prop has its own DFPlayer and SD card: sd-card/props/<prop>/01/
        for prop, slots in props_pack().items():
            for slot, sig in slots.items():
                loop = prop == "cauldron" and slot == 1
                write_mp3(normalise(sig, -18 if loop else -16), os.path.join(ROOT, "sd-card", "props", prop, "01", "%03d.mp3" % slot),
                          lead=0.0 if loop else 0.1)
                print("wrote", prop, slot)


if __name__ == "__main__":
    main()
