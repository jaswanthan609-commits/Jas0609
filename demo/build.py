"""Offline demo clips (no paid APIs): Kokoro voice, self-drawn visuals, facepipe assembly.

Run from demo/: python engrave.py moon oven river lamps street && python cards.py && python build.py sleep|nri
"""
import os, sys, subprocess, numpy as np, soundfile as sf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from facepipe.config import load_config
from facepipe.assemble import scene_clip, final_render
from facepipe.captions import build_ass
from kokoro_onnx import Kokoro
HERE = Path(__file__).parent
MODELS = Path(os.environ.get("KOKORO_DIR", HERE / "models"))  # kokoro-v1.0.onnx + voices-v1.0.bin from the kokoro-onnx GitHub release
K = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))

def pad(seconds, out, base=(110, 165, 220), vol=0.06, sr=44100):
    """Self-made soft ambient pad (stand-in for the music library)."""
    t = np.arange(int(seconds * sr)) / sr
    sig = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.07 * t * (i + 1))) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + i)) for i, f in enumerate(base))
    sig += 0.3 * np.sin(2 * np.pi * base[0] * 2.003 * t)
    sig = sig / np.abs(sig).max() * vol
    fade = np.minimum(1, np.minimum(t / 3, (seconds - t) / 3))
    sf.write(out, np.stack([sig * fade] * 2, 1), sr)

def make(name, channel, voice, speed, lang, scenes, gap, music_base, music_vol):
    cfg = load_config(channel)
    cfg.music_volume = 1.0
    work = HERE / name; work.mkdir(exist_ok=True)
    audio, clips, caps = [], [], []
    sr = 24000
    for i, (text, img, head) in enumerate(scenes):
        s, sr = K.create(text, voice=voice, speed=speed, lang=lang)
        s = np.concatenate([s, np.zeros(int(gap * sr), np.float32)])
        dur = len(s) / sr
        audio.append(s)
        clips.append(scene_clip(HERE / img, dur, 1920, 1080, work / f"c{i}.mp4"))
        caps.append((text, dur, head))
    voice_wav = work / "voice.wav"; sf.write(voice_wav, np.concatenate(audio), sr)
    total = sum(c[1] for c in caps)
    listing = work / "list.txt"; listing.write_text("".join(f"file '{c}'\n" for c in clips))
    video = work / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(video)], check=True)
    music = work / "pad.wav"; pad(total + 1, music, music_base, music_vol)
    ass = build_ass(cfg, caps, 1920, 1080, work / "subs.ass")
    out = HERE / f"{name}.mp4"
    final_render(cfg, video, voice_wav, ass, out, music)
    print(name, round(total, 1), "s", cfg.font_name)

SLEEP = [
 ("Settle in, and let your shoulders soften. Tonight, we drift back nearly two thousand years, to the city of Rome, in the quiet hour before dawn.", "img_moon.jpg", ""),
 ("The streets are dark and still. High above the tiled rooftops, a pale moon hangs over the seven hills.", "img_moon.jpg", ""),
 ("In a narrow lane, a baker is already awake. He sweeps the ashes from his brick oven, and lays in fresh wood. Slowly, the bricks begin to glow, warm and orange.", "img_oven.jpg", ""),
 ("Down by the river Tiber, the water moves gently under the stone arches of the bridge, carrying a small boat toward the sea.", "img_river.jpg", ""),
 ("Heavy carts are only allowed into the city at night. So, in the last dark hours, their wooden wheels roll softly over the paving stones, bringing grain, and wine, and firewood.", "img_street.jpg", ""),
 ("In a small room, a clay oil lamp burns low on the table. Its little flame flickers, and steadies, and flickers again. Breathe slowly. There is nowhere you need to be.", "img_lamps.jpg", ""),
]
NRI = [
 ("NRE or NRO? If you're an Indian living abroad, picking the wrong account can cost you tax. Here are three differences that matter.", "nri_0.png", ""),
 ("One. Where the money comes from. An NRE account is for money you earn abroad and bring into India. An NRO account is for money you earn in India, like rent, dividends, or a pension.", "nri_1.png", ""),
 ("Two. Tax in India. Interest on an NRE account is tax free in India. Interest on an NRO account is taxable, and the bank usually deducts thirty percent, plus surcharge and cess. A tax treaty can lower that, if you submit the right forms.", "nri_2.png", ""),
 ("Three. Sending money back. NRE money, with its interest, can go back abroad freely. From an NRO account, you can send up to one million US dollars per financial year, after tax, with forms fifteen C A and fifteen C B.", "nri_3.png", ""),
 ("One catch. Tax free in India doesn't mean tax free everywhere. If you live in the US, for example, you still report NRE interest on your US tax return.", "nri_4.png", ""),
 ("The official sources are on screen. This is education, not advice. Follow for more.", "nri_5.png", ""),
]
if __name__ == "__main__":
    which = sys.argv[1]
    if which == "sleep":
        make("slow-history-demo", "sleepy-history", "bm_george", 0.82, "en-gb", SLEEP, 1.4, (98, 147, 196), 0.12)
    else:
        make("nri-money-demo", "nri-money", "am_michael", 1.0, "en-us", NRI, 0.5, (130, 195, 260), 0.05)
