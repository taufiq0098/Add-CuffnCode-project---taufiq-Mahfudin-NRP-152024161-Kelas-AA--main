"""
CuffnCode — Unit Tests for Signal Processing
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from src.signal_processing import (
    bandpass_filter, lowpass_filter,
    extract_envelope, find_oscillation_peaks, compute_heart_rate
)


FS = 100.0  # Hz


def make_test_signal(duration=10.0, fs=FS):
    """Create a synthetic signal: 2 Hz sine + 80 mmHg DC."""
    t = np.linspace(0, duration, int(duration * fs))
    dc = 80.0 * np.ones_like(t)
    osc = 5.0 * np.sin(2 * np.pi * 2.0 * t)   # 2 Hz cardiac oscillation
    noise = np.random.normal(0, 0.3, len(t))
    return t, dc + osc + noise


class TestBandpassFilter:
    def test_output_shape(self):
        _, sig = make_test_signal()
        result = bandpass_filter(sig, FS)
        assert result.shape == sig.shape

    def test_removes_dc(self):
        _, sig = make_test_signal()
        result = bandpass_filter(sig, FS)
        # Mean should be near 0 (DC removed)
        assert abs(result.mean()) < 5.0

    def test_preserves_cardiac_frequency(self):
        t, _ = make_test_signal()
        pure_cardiac = 5.0 * np.sin(2 * np.pi * 2.0 * t)
        result = bandpass_filter(pure_cardiac, FS, lowcut=0.5, highcut=10.0)
        # Should not attenuate 2 Hz significantly
        assert result.std() > 1.0


class TestLowpassFilter:
    def test_output_shape(self):
        _, sig = make_test_signal()
        result = lowpass_filter(sig, FS)
        assert result.shape == sig.shape

    def test_smoothing(self):
        _, sig = make_test_signal()
        result = lowpass_filter(sig, FS, cutoff=0.3)
        # Lowpass output should have lower variance than input
        assert result.std() <= sig.std()


class TestEnvelopeExtraction:
    def test_positive_output(self):
        _, sig = make_test_signal()
        osc = bandpass_filter(sig, FS)
        env = extract_envelope(osc, FS)
        assert np.all(env >= 0)

    def test_envelope_shape(self):
        _, sig = make_test_signal()
        osc = bandpass_filter(sig, FS)
        env = extract_envelope(osc, FS)
        assert env.shape == sig.shape


class TestPeakDetection:
    def test_finds_peaks_in_sine(self):
        t = np.linspace(0, 10, int(10 * FS))
        sine = 3.0 * np.sin(2 * np.pi * 1.2 * t)  # 1.2 Hz = 72 BPM
        peaks, _ = find_oscillation_peaks(sine, FS)
        assert len(peaks) >= 5  # expect ~12 peaks in 10 sec

    def test_heart_rate_estimate(self):
        t = np.linspace(0, 10, int(10 * FS))
        sine = 3.0 * np.sin(2 * np.pi * 1.2 * t)  # 1.2 Hz = 72 BPM
        peaks, _ = find_oscillation_peaks(sine, FS)
        hr = compute_heart_rate(peaks, FS)
        assert 60 < hr < 84  # should be close to 72 BPM

    def test_no_peaks_flat_signal(self):
        flat = np.ones(int(5 * FS)) * 80.0
        peaks, _ = find_oscillation_peaks(flat, FS)
        assert len(peaks) == 0
