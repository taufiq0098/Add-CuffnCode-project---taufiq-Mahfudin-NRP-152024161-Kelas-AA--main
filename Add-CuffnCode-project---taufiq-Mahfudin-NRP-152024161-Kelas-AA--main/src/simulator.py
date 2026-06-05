"""
CuffnCode — Signal Simulator
Generates synthetic oscillometric blood pressure waveform data
for demonstration without physical hardware.
"""

import numpy as np
from dataclasses import dataclass
from typing import Generator


@dataclass
class SimConfig:
    """Configuration for synthetic waveform generation."""
    target_sbp: float = 120.0    # mmHg
    target_dbp: float = 80.0     # mmHg
    heart_rate: float = 72.0     # BPM
    inflate_rate: float = 10.0   # mmHg/sec
    max_pressure: float = 180.0  # mmHg
    deflate_rate: float = 2.5    # mmHg/sec
    sample_rate: float = 100.0   # Hz
    noise_std: float = 0.3       # mmHg noise


def _oscillometric_amplitude(pressure: float, sbp: float, dbp: float) -> float:
    """
    Model oscillation amplitude as a Gaussian centered at MAP.
    Returns the peak-to-peak oscillation amplitude at the given cuff pressure.
    """
    map_val = dbp + (sbp - dbp) / 3.0
    sigma = (sbp - dbp) / 2.5
    max_amp = 8.0  # peak amplitude in mmHg at MAP
    return max_amp * np.exp(-0.5 * ((pressure - map_val) / sigma) ** 2)


def generate_waveform(config: SimConfig = None) -> Generator:
    """
    Generator that yields (time, pressure) samples simulating a full
    measurement cycle: inflate → plateau → deflate.
    """
    if config is None:
        config = SimConfig()

    sbp = config.target_sbp + np.random.normal(0, 2)
    dbp = config.target_dbp + np.random.normal(0, 1)
    hr = config.heart_rate + np.random.normal(0, 3)

    dt = 1.0 / config.sample_rate
    beat_interval = 60.0 / hr  # seconds per beat

    # ── Phase 1: Inflate ─────────────────────────────────────────────────────
    t = 0.0
    pressure = 0.0
    last_beat_t = 0.0

    while pressure < config.max_pressure:
        pressure += config.inflate_rate * dt
        osc_amp = _oscillometric_amplitude(pressure, sbp, dbp) * 0.1  # small during inflate
        # Heartbeat pulses
        if t - last_beat_t >= beat_interval:
            last_beat_t = t
        beat_phase = (t - last_beat_t) / beat_interval
        oscillation = osc_amp * np.exp(-beat_phase * 8) * np.sin(beat_phase * 2 * np.pi * 3)
        noise = np.random.normal(0, config.noise_std)
        yield (t, pressure + oscillation + noise, "inflate")
        t += dt

    # ── Phase 2: Brief Plateau ────────────────────────────────────────────────
    hold_end = t + 0.5
    while t < hold_end:
        noise = np.random.normal(0, config.noise_std)
        yield (t, pressure + noise, "plateau")
        t += dt

    # ── Phase 3: Controlled Deflate ──────────────────────────────────────────
    while pressure > 0:
        pressure -= config.deflate_rate * dt
        pressure = max(pressure, 0.0)
        osc_amp = _oscillometric_amplitude(pressure, sbp, dbp)
        beat_phase = ((t - last_beat_t) % beat_interval) / beat_interval
        if t - last_beat_t >= beat_interval:
            last_beat_t = t
        oscillation = osc_amp * np.exp(-beat_phase * 5) * np.sin(beat_phase * 2 * np.pi * 2)
        noise = np.random.normal(0, config.noise_std)
        yield (t, pressure + oscillation + noise, "deflate")
        t += dt


def get_sample_waveform(config: SimConfig = None, max_points: int = 10000):
    """Return full arrays of time, pressure, and phase for a complete measurement."""
    if config is None:
        config = SimConfig()
    times, pressures, phases = [], [], []
    for t, p, phase in generate_waveform(config):
        times.append(t)
        pressures.append(p)
        phases.append(phase)
        if len(times) >= max_points:
            break
    return np.array(times), np.array(pressures), phases
