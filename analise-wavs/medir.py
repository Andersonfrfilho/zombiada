"""Mede cada arquivo de áudio: duração, taxa, canais, pico, RMS, clipping, piso de ruído, centroide, largura de banda,
ataque, posição do pico e energia grave; guarda também um hash do PCM e uma impressão digital a 8 kHz para achar duplicatas.

Uso: python medir.py <saida.json> <pasta> [<pasta> ...]
"""
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

AUDIO_SUFFIXES = {'.wav', '.ogg', '.flac'}
FINGERPRINT_RATE = 8000
FINGERPRINT_SECONDS = 4


def probe(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate,channels', '-of', 'csv=p=0', str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip().split(',')
    return int(out[0]), int(out[1])


def decode(path: Path, rate: int | None = None, channels: int | None = None) -> np.ndarray:
    args = ['ffmpeg', '-v', 'error', '-i', str(path)]
    if channels:
        args += ['-ac', str(channels)]
    if rate:
        args += ['-ar', str(rate)]
    raw = subprocess.run(args + ['-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def to_db(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-7)))


def spectrum_stats(mono: np.ndarray, rate: int) -> tuple[float, float, float]:
    frame, hop = 2048, 512
    if len(mono) < frame:
        mono = np.pad(mono, (0, frame - len(mono)))
    frames = np.lib.stride_tricks.sliding_window_view(mono, frame)[::hop] * np.hanning(frame)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    freqs = np.fft.rfftfreq(frame, 1 / rate)
    total = power.sum()
    if total <= 0:
        return 0.0, 0.0, 0.0
    weights = power.sum(axis=0) / total
    centroid = float((weights * freqs).sum())
    bandwidth = float(np.sqrt((weights * (freqs - centroid) ** 2).sum()))
    low_share = float(weights[freqs < 150].sum())
    return centroid, bandwidth, low_share


def envelope_stats(mono: np.ndarray, rate: int) -> dict:
    window = max(1, int(rate * 0.01))
    count = max(1, len(mono) // window)
    env = np.sqrt((mono[: count * window].reshape(count, window) ** 2).mean(axis=1)) if len(mono) >= window else np.array([np.abs(mono).max(initial=0)])
    peak_index = int(env.argmax())
    peak = env[peak_index] if len(env) else 0
    onset = int(np.argmax(env > peak * 0.1)) if peak > 0 else 0
    audible = np.nonzero(env > peak * 0.03)[0]
    end = int(audible[-1]) if len(audible) else 0
    frame_db = 20 * np.log10(np.maximum(env, 1e-7))
    return {
        'ataque_s': round((peak_index - onset) * 0.01, 3),
        'pico_em_s': round(peak_index * 0.01, 3),
        'pico_relativo': round(peak_index / max(end, 1), 2),
        'som_util_s': round((end - onset) * 0.01, 3),
        'piso_ruido_dbfs': round(max(float(np.percentile(frame_db, 10)), -90.0), 1),
    }


def measure(path_text: str) -> dict:
    path = Path(path_text)
    try:
        rate, channels = probe(path)
        samples = decode(path).reshape(-1, channels)
    except Exception as error:  # arquivo que o ffmpeg não lê vira linha com erro, não derruba o lote
        return {'caminho': path_text, 'erro': str(error)[:200]}
    mono = samples.mean(axis=1)
    peak = float(np.abs(samples).max(initial=0))
    rms = float(np.sqrt((mono ** 2).mean())) if len(mono) else 0.0
    centroid, bandwidth, low_share = spectrum_stats(mono, rate)
    fingerprint = decode(path, FINGERPRINT_RATE, 1)[: FINGERPRINT_RATE * FINGERPRINT_SECONDS]
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16).tobytes()
    return {
        'caminho': path_text,
        'duracao_s': round(len(mono) / rate, 3),
        'taxa_hz': rate,
        'canais': channels,
        'pico_dbfs': round(to_db(peak), 2),
        'rms_dbfs': round(to_db(rms), 2),
        'amostras_clipadas': int((np.abs(samples) >= 0.999).sum()),
        'centroide_hz': round(centroid),
        'largura_banda_hz': round(bandwidth),
        'grave_150hz': round(low_share, 3),
        'hash': hashlib.sha1(pcm).hexdigest()[:12],
        'impressao': np.round(fingerprint, 4).tolist(),
        **envelope_stats(mono, rate),
    }


def main() -> None:
    output, folders = Path(sys.argv[1]), sys.argv[2:]
    paths = sorted(str(p) for folder in folders for p in Path(folder).rglob('*') if p.suffix.lower() in AUDIO_SUFFIXES)
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(measure, paths, chunksize=8))
    output.write_text(json.dumps(rows))
    print(f'{len(rows)} arquivos medidos, {sum("erro" in r for r in rows)} com erro')


if __name__ == '__main__':
    main()
