"""
CuffnCode — Data Logger
Saves measurement sessions to CSV and JSON for offline analysis.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import numpy as np


class DataLogger:
    """Persists waveform data and BP results to disk."""

    def __init__(self, output_dir: str = "data/recordings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._waveform_buffer: List[Tuple] = []

    def log_sample(self, time_s: float, pressure_mmhg: float, phase: str = ""):
        """Add a single sample to the buffer."""
        self._waveform_buffer.append((time_s, pressure_mmhg, phase))

    def log_samples_bulk(self, times, pressures, phases=None):
        """Log arrays of samples at once."""
        if phases is None:
            phases = [""] * len(times)
        for t, p, ph in zip(times, pressures, phases):
            self._waveform_buffer.append((t, float(p), ph))

    def save_waveform(self) -> str:
        """Write buffered waveform to CSV. Returns the filepath."""
        fname = self.output_dir / f"waveform_{self._session_id}.csv"
        with open(fname, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["time_s", "pressure_mmhg", "phase"])
            writer.writerows(self._waveform_buffer)
        return str(fname)

    def save_result(self, result) -> str:
        """Write BPResult to JSON. Returns the filepath."""
        fname = self.output_dir / f"result_{self._session_id}.json"
        data = {
            "session_id": self._session_id,
            "timestamp": datetime.now().isoformat(),
            "sbp_mmhg": result.sbp,
            "dbp_mmhg": result.dbp,
            "map_mmhg": result.map_val,
            "heart_rate_bpm": result.heart_rate,
            "classification": result.classification,
            "valid": result.valid,
        }
        with open(fname, 'w') as f:
            json.dump(data, f, indent=2)
        return str(fname)

    def clear(self):
        """Reset buffer for a new session."""
        self._waveform_buffer.clear()
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def load_waveform(filepath: str):
        """Load a previously saved waveform CSV. Returns (times, pressures, phases)."""
        times, pressures, phases = [], [], []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                times.append(float(row['time_s']))
                pressures.append(float(row['pressure_mmhg']))
                phases.append(row.get('phase', ''))
        return np.array(times), np.array(pressures), phases
