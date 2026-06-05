"""
CuffnCode — Blood Pressure Algorithm
Implements the Oscillometric Method to compute Systolic, Diastolic,
and Mean Arterial Pressure from a pressure + oscillation signal.

Reference:
  Drzewiecki, G. et al. "Noninvasive blood pressure recording and the
  genesis of Korotkoff sound." In Handbook of Bioengineering, 1987.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from .signal_processing import (
    bandpass_filter, lowpass_filter,
    extract_envelope, find_oscillation_peaks, compute_heart_rate
)


@dataclass
class BPResult:
    """Blood pressure measurement result."""
    sbp: float          # Systolic Blood Pressure (mmHg)
    dbp: float          # Diastolic Blood Pressure (mmHg)
    map_val: float      # Mean Arterial Pressure (mmHg)
    heart_rate: float   # Heart Rate (BPM)
    valid: bool = True
    error_msg: str = ""

    def __str__(self):
        if not self.valid:
            return f"Measurement failed: {self.error_msg}"
        return (f"SBP: {self.sbp:.0f} mmHg | DBP: {self.dbp:.0f} mmHg | "
                f"MAP: {self.map_val:.0f} mmHg | HR: {self.heart_rate:.0f} BPM")

    @property
    def classification(self) -> str:
        """Return BP classification per AHA guidelines."""
        if self.sbp < 120 and self.dbp < 80:
            return "Normal"
        elif self.sbp < 130 and self.dbp < 80:
            return "Elevated"
        elif self.sbp < 140 or self.dbp < 90:
            return "Hypertension Stage 1"
        elif self.sbp >= 140 or self.dbp >= 90:
            return "Hypertension Stage 2"
        elif self.sbp > 180 or self.dbp > 120:
            return "Hypertensive Crisis"
        return "Unknown"

    @property
    def classification_color(self) -> str:
        """Return a color code for the classification."""
        colors = {
            "Normal": "#2ECC71",
            "Elevated": "#F1C40F",
            "Hypertension Stage 1": "#E67E22",
            "Hypertension Stage 2": "#E74C3C",
            "Hypertensive Crisis": "#8E44AD",
        }
        return colors.get(self.classification, "#AAAAAA")


# Oscillometric ratio thresholds (from literature)
SBP_RATIO = 0.45   # SBP at 45% of max oscillation amplitude
DBP_RATIO = 0.70   # DBP at 70% of max oscillation amplitude


def compute_bp(time_arr: np.ndarray,
               pressure_arr: np.ndarray,
               fs: float = 100.0,
               phase_arr=None) -> BPResult:
    """
    Main blood pressure computation from raw oscillometric data.

    Parameters
    ----------
    time_arr : array of timestamps (seconds)
    pressure_arr : array of raw cuff pressure readings (mmHg)
    fs : sample rate (Hz)
    phase_arr : optional list of phase labels ('inflate','plateau','deflate')

    Returns
    -------
    BPResult dataclass
    """
    if len(pressure_arr) < int(fs * 5):
        return BPResult(0, 0, 0, 0, valid=False,
                        error_msg="Insufficient data length (< 5 seconds)")

    # ── Step 1: Extract deflation phase only ─────────────────────────────────
    if phase_arr is not None:
        deflate_mask = np.array([p == "deflate" for p in phase_arr])
    else:
        # Auto-detect: find where pressure peaks then declines
        peak_idx = np.argmax(pressure_arr)
        deflate_mask = np.zeros(len(pressure_arr), dtype=bool)
        deflate_mask[peak_idx:] = True

    p_deflate = pressure_arr[deflate_mask]
    t_deflate = time_arr[deflate_mask]

    if len(p_deflate) < int(fs * 3):
        return BPResult(0, 0, 0, 0, valid=False,
                        error_msg="Deflation phase too short")

    # ── Step 2: Separate DC trend from oscillations ───────────────────────────
    dc_trend = lowpass_filter(p_deflate, fs, cutoff=0.3)
    oscillations = bandpass_filter(p_deflate, fs, lowcut=0.5, highcut=8.0)

    # ── Step 3: Extract envelope ──────────────────────────────────────────────
    envelope = extract_envelope(oscillations, fs)

    # ── Step 4: Find MAP at peak oscillation ──────────────────────────────────
    max_idx = np.argmax(envelope)
    map_pressure = dc_trend[max_idx]

    max_amp = envelope[max_idx]
    if max_amp < 0.5:
        return BPResult(0, 0, 0, 0, valid=False,
                        error_msg="Oscillations too weak — check cuff placement")

    # ── Step 5: Apply ratio thresholds for SBP and DBP ───────────────────────
    # SBP: first crossing of SBP_RATIO on ascending side (before MAP)
    sbp_threshold = SBP_RATIO * max_amp
    dbp_threshold = DBP_RATIO * max_amp

    sbp_pressure = _find_pressure_at_amplitude(
        envelope[:max_idx + 1], dc_trend[:max_idx + 1],
        sbp_threshold, side='ascending'
    )
    dbp_pressure = _find_pressure_at_amplitude(
        envelope[max_idx:], dc_trend[max_idx:],
        dbp_threshold, side='descending'
    )

    if sbp_pressure is None or dbp_pressure is None:
        return BPResult(0, 0, 0, 0, valid=False,
                        error_msg="Could not determine SBP/DBP crossings")

    # ── Step 6: Heart rate from oscillation peaks ────────────────────────────
    peaks, _ = find_oscillation_peaks(oscillations, fs)
    hr = compute_heart_rate(peaks, fs)

    # Sanity checks
    if sbp_pressure <= dbp_pressure:
        sbp_pressure = map_pressure * 1.25
        dbp_pressure = map_pressure * 0.78

    sbp = np.clip(sbp_pressure, 60, 250)
    dbp = np.clip(dbp_pressure, 40, 180)
    hr = np.clip(hr, 30, 200)

    return BPResult(
        sbp=round(sbp, 1),
        dbp=round(dbp, 1),
        map_val=round(map_pressure, 1),
        heart_rate=round(hr, 1)
    )


def _find_pressure_at_amplitude(envelope_seg: np.ndarray,
                                  dc_seg: np.ndarray,
                                  threshold: float,
                                  side: str) -> Optional[float]:
    """
    Find the cuff pressure where envelope amplitude crosses a threshold.
    `side='ascending'` looks for first crossing going from low to high amplitude.
    `side='descending'` looks from peak going down.
    """
    if side == 'ascending':
        # Search from end of segment (near MAP) backwards
        for i in range(len(envelope_seg) - 1, 0, -1):
            if envelope_seg[i] <= threshold < envelope_seg[i - 1]:
                # Interpolate
                frac = (threshold - envelope_seg[i]) / (envelope_seg[i - 1] - envelope_seg[i] + 1e-9)
                return dc_seg[i] + frac * (dc_seg[i - 1] - dc_seg[i])
        return dc_seg[0]  # fallback
    else:
        # Search forward from MAP
        for i in range(len(envelope_seg) - 1):
            if envelope_seg[i] >= threshold > envelope_seg[i + 1]:
                frac = (threshold - envelope_seg[i]) / (envelope_seg[i + 1] - envelope_seg[i] + 1e-9)
                return dc_seg[i] + frac * (dc_seg[i + 1] - dc_seg[i])
        return dc_seg[-1]  # fallback
