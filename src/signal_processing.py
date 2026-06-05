"""
CuffnCode — Signal Processing Module
Filters and extracts the oscillometric envelope from the raw pressure signal.
"""

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, savgol_filter


def bandpass_filter(signal: np.ndarray, fs: float,
                    lowcut: float = 0.5, highcut: float = 10.0,
                    order: int = 4) -> np.ndarray:
    """
    Apply a Butterworth bandpass filter to isolate oscillometric frequencies.
    The cardiac oscillations are typically 0.5–5 Hz (30–300 BPM).
    """
    nyq = fs / 2.0
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)


def lowpass_filter(signal: np.ndarray, fs: float,
                   cutoff: float = 0.5, order: int = 4) -> np.ndarray:
    """Extract the slowly-varying pressure envelope (DC trend)."""
    nyq = fs / 2.0
    b, a = butter(order, cutoff / nyq, btype='low')
    return filtfilt(b, a, signal)


def extract_envelope(oscillations: np.ndarray, fs: float) -> np.ndarray:
    """
    Compute the oscillometric envelope as the peak-to-peak amplitude
    smoothed over each heartbeat window.
    Uses the absolute value + lowpass approach for simplicity.
    """
    rectified = np.abs(oscillations)
    window = max(3, int(fs * 0.5))  # ~0.5 s window
    if window % 2 == 0:
        window += 1
    envelope = savgol_filter(rectified, window_length=window, polyorder=2)
    return np.clip(envelope, 0, None)


def find_oscillation_peaks(oscillations: np.ndarray, fs: float):
    """
    Find the indices of oscillometric peaks in the filtered signal.
    Returns peak indices and their properties.
    """
    min_distance = int(fs * 0.4)  # minimum 400 ms between peaks (max ~150 BPM)
    peaks, props = find_peaks(oscillations,
                               distance=min_distance,
                               prominence=0.2)
    return peaks, props


def compute_heart_rate(peak_indices: np.ndarray, fs: float) -> float:
    """Estimate heart rate from inter-peak intervals."""
    if len(peak_indices) < 2:
        return 0.0
    intervals = np.diff(peak_indices) / fs  # in seconds
    mean_interval = np.median(intervals)
    return 60.0 / mean_interval if mean_interval > 0 else 0.0
