"""
CuffnCode — Main Dashboard GUI
A modern blood pressure monitoring dashboard built with customtkinter.
"""

import tkinter as tk
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import threading
import time
import sys
import os
from collections import deque
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import SimConfig, generate_waveform
from src.signal_processing import bandpass_filter, lowpass_filter, extract_envelope
from src.bp_algorithm import compute_bp, BPResult
from src.data_logger import DataLogger

# ── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Color palette
COLORS = {
    "bg_primary":    "#0D1117",
    "bg_secondary":  "#161B22",
    "bg_card":       "#1C2230",
    "accent_blue":   "#2188FF",
    "accent_teal":   "#00B4D8",
    "accent_green":  "#2ECC71",
    "accent_orange": "#F39C12",
    "accent_red":    "#E74C3C",
    "text_primary":  "#E6EDF3",
    "text_muted":    "#8B949E",
    "border":        "#30363D",
    "plot_bg":       "#0D1117",
    "plot_grid":     "#21262D",
    "waveform_raw":  "#2188FF",
    "waveform_dc":   "#F39C12",
    "waveform_osc":  "#2ECC71",
}

SAMPLE_RATE = 100.0  # Hz


class MetricCard(ctk.CTkFrame):
    """A styled card displaying a single metric value."""

    def __init__(self, parent, label: str, unit: str, color: str, **kwargs):
        super().__init__(parent, corner_radius=16,
                         fg_color=COLORS["bg_card"],
                         border_width=1, border_color=COLORS["border"],
                         **kwargs)
        self._label = label
        self._unit = unit
        self._color = color

        # Header
        header = ctk.CTkLabel(self, text=label.upper(),
                               font=ctk.CTkFont("Segoe UI", 11, weight="normal"),
                               text_color=COLORS["text_muted"])
        header.pack(pady=(16, 0), padx=16)

        # Value
        self._value_var = tk.StringVar(value="--")
        self._value_label = ctk.CTkLabel(
            self, textvariable=self._value_var,
            font=ctk.CTkFont("Segoe UI", 52, weight="bold"),
            text_color=color
        )
        self._value_label.pack(pady=(2, 0), padx=16)

        # Unit
        unit_label = ctk.CTkLabel(self, text=unit,
                                   font=ctk.CTkFont("Segoe UI", 13),
                                   text_color=COLORS["text_muted"])
        unit_label.pack(pady=(0, 16), padx=16)

    def set_value(self, val: float):
        if val > 0:
            self._value_var.set(f"{val:.0f}")
        else:
            self._value_var.set("--")

    def flash(self, color: str = None):
        """Brief color flash animation on new measurement."""
        c = color or self._color
        self._value_label.configure(text_color=c)
        self.after(600, lambda: self._value_label.configure(text_color=self._color))


class StatusBadge(ctk.CTkLabel):
    """Animated status indicator badge."""

    STATUS_COLORS = {
        "Idle":        ("#4A5568", "⏸  Idle"),
        "Inflating":   ("#2188FF", "⬆  Inflating"),
        "Deflating":   ("#F39C12", "⬇  Deflating"),
        "Processing":  ("#00B4D8", "⚙  Processing"),
        "Done":        ("#2ECC71", "✓  Measurement Complete"),
        "Error":       ("#E74C3C", "✗  Error"),
        "Simulating":  ("#9B59B6", "◉  Simulating"),
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent,
                         font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                         **kwargs)
        self.set_status("Idle")

    def set_status(self, status: str):
        color, text = self.STATUS_COLORS.get(status, ("#8B949E", status))
        self.configure(text=text, text_color=color)


class WaveformPanel(ctk.CTkFrame):
    """Embeds a scrolling matplotlib waveform plot."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_secondary"],
                         corner_radius=16, border_width=1,
                         border_color=COLORS["border"], **kwargs)
        self._setup_plot()
        self._data_t: deque = deque(maxlen=1500)
        self._data_p: deque = deque(maxlen=1500)
        self._data_osc: deque = deque(maxlen=1500)
        self._data_dc: deque = deque(maxlen=1500)
        self._show_osc = False
        self._show_dc = True

    def _setup_plot(self):
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(10, 3.2), dpi=96,
                          facecolor=COLORS["plot_bg"])
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(COLORS["plot_bg"])
        self.ax.tick_params(colors=COLORS["text_muted"], labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS["border"])
        self.ax.set_xlabel("Time (s)", color=COLORS["text_muted"], fontsize=10)
        self.ax.set_ylabel("Pressure (mmHg)", color=COLORS["text_muted"], fontsize=10)
        self.ax.grid(True, color=COLORS["plot_grid"], linewidth=0.5, alpha=0.8)
        self.ax.set_ylim(-5, 200)
        self.ax.set_xlim(0, 30)

        self.line_raw, = self.ax.plot([], [], color=COLORS["waveform_raw"],
                                       linewidth=1.2, label="Raw Pressure", alpha=0.9)
        self.line_dc, = self.ax.plot([], [], color=COLORS["waveform_dc"],
                                      linewidth=1.8, label="DC Trend",
                                      linestyle='--', alpha=0.8)
        self.line_osc, = self.ax.plot([], [], color=COLORS["waveform_osc"],
                                       linewidth=1.0, label="Oscillations", alpha=0.7)
        self.legend = self.ax.legend(loc='upper right', fontsize=8,
                                      facecolor=COLORS["bg_card"],
                                      edgecolor=COLORS["border"],
                                      labelcolor=COLORS["text_primary"])
        self.fig.tight_layout(pad=1.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=4, pady=4)

    def add_samples(self, times, pressures, dc=None, osc=None):
        self._data_t.extend(times)
        self._data_p.extend(pressures)
        if dc is not None:
            self._data_dc.extend(dc)
        if osc is not None:
            self._data_osc.extend(osc)

    def refresh(self):
        if len(self._data_t) < 2:
            return
        t_arr = np.array(self._data_t)
        p_arr = np.array(self._data_p)

        self.line_raw.set_data(t_arr, p_arr)

        if self._data_dc and len(self._data_dc) == len(t_arr):
            dc_arr = np.array(self._data_dc)
            self.line_dc.set_data(t_arr, dc_arr)
        else:
            self.line_dc.set_data([], [])

        if self._show_osc and self._data_osc and len(self._data_osc) == len(t_arr):
            osc_arr = np.array(self._data_osc) + 100  # offset for visibility
            self.line_osc.set_data(t_arr, osc_arr)
        else:
            self.line_osc.set_data([], [])

        # Auto-scroll x-axis
        t_max = t_arr[-1]
        window = 30.0
        self.ax.set_xlim(max(0, t_max - window), max(30, t_max))
        self.canvas.draw_idle()

    def clear(self):
        self._data_t.clear()
        self._data_p.clear()
        self._data_dc.clear()
        self._data_osc.clear()
        self.line_raw.set_data([], [])
        self.line_dc.set_data([], [])
        self.line_osc.set_data([], [])
        self.ax.set_xlim(0, 30)
        self.canvas.draw_idle()


class CuffnCodeApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("CuffnCode — Blood Pressure Monitor")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(fg_color=COLORS["bg_primary"])

        self._sim_thread: threading.Thread = None
        self._sim_running = False
        self._all_t = []
        self._all_p = []
        self._all_phase = []
        self._logger = DataLogger()
        self._last_result: BPResult = None
        self._refresh_rate_ms = 80  # ms between plot updates

        self._build_ui()
        self._start_refresh_loop()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        self._build_main_content()
        self._build_bottom_bar()

    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                               height=64, corner_radius=0,
                               border_width=0)
        topbar.pack(fill='x', padx=0, pady=0)
        topbar.pack_propagate(False)

        # Logo
        logo = ctk.CTkLabel(topbar, text="💉  CuffnCode",
                             font=ctk.CTkFont("Segoe UI", 22, weight="bold"),
                             text_color=COLORS["accent_blue"])
        logo.pack(side='left', padx=24)

        subtitle = ctk.CTkLabel(topbar, text="Blood Pressure Monitor  ·  Oscillometric Method",
                                 font=ctk.CTkFont("Segoe UI", 12),
                                 text_color=COLORS["text_muted"])
        subtitle.pack(side='left', padx=0)

        # Timestamp
        self._time_label = ctk.CTkLabel(topbar, text="",
                                         font=ctk.CTkFont("Segoe UI", 12),
                                         text_color=COLORS["text_muted"])
        self._time_label.pack(side='right', padx=24)
        self._update_clock()

    def _build_main_content(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill='both', expand=True, padx=16, pady=(12, 0))

        # ── Left Panel: Controls ──────────────────────────────────────────────
        left = ctk.CTkFrame(main, width=280, fg_color=COLORS["bg_secondary"],
                             corner_radius=16, border_width=1,
                             border_color=COLORS["border"])
        left.pack(side='left', fill='y', padx=(0, 12))
        left.pack_propagate(False)
        self._build_controls(left)

        # ── Right Panel: Waveform + Metrics ──────────────────────────────────
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side='left', fill='both', expand=True)
        self._build_metrics(right)
        self._build_waveform(right)

    def _build_controls(self, parent):
        ctk.CTkLabel(parent, text="CONTROLS",
                     font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(20, 4), padx=20, anchor='w')

        # Mode selector
        ctk.CTkLabel(parent, text="Mode",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_primary"]).pack(pady=(12, 4), padx=20, anchor='w')
        self._mode_var = ctk.StringVar(value="Simulation")
        mode_menu = ctk.CTkOptionMenu(parent,
                                       values=["Simulation", "Hardware (Serial)"],
                                       variable=self._mode_var,
                                       width=220,
                                       fg_color=COLORS["bg_card"],
                                       button_color=COLORS["accent_blue"])
        mode_menu.pack(padx=20, pady=(0, 12))

        # Serial port (shown in hardware mode)
        ctk.CTkLabel(parent, text="Serial Port",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_primary"]).pack(pady=(0, 4), padx=20, anchor='w')
        self._port_entry = ctk.CTkEntry(parent, placeholder_text="e.g. COM3",
                                         width=220, fg_color=COLORS["bg_card"])
        self._port_entry.pack(padx=20, pady=(0, 16))

        # Simulation config
        ctk.CTkLabel(parent, text="─── Simulation Settings ───",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["text_muted"]).pack(pady=(4, 8), padx=20)

        self._sbp_slider = self._make_slider(parent, "Target SBP (mmHg)", 90, 180, 120)
        self._dbp_slider = self._make_slider(parent, "Target DBP (mmHg)", 50, 120, 80)
        self._hr_slider  = self._make_slider(parent, "Heart Rate (BPM)", 40, 130, 72)

        # Buttons
        self._start_btn = ctk.CTkButton(
            parent, text="▶  Start Measurement",
            font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            fg_color=COLORS["accent_blue"], hover_color="#1A6FCC",
            height=44, width=220, corner_radius=12,
            command=self._on_start
        )
        self._start_btn.pack(padx=20, pady=(20, 8))

        self._stop_btn = ctk.CTkButton(
            parent, text="■  Stop",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=COLORS["bg_card"], hover_color=COLORS["accent_red"],
            text_color=COLORS["text_muted"], height=36, width=220,
            corner_radius=12, command=self._on_stop, state='disabled'
        )
        self._stop_btn.pack(padx=20, pady=(0, 8))

        save_btn = ctk.CTkButton(
            parent, text="💾  Save Last Recording",
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=COLORS["bg_card"], hover_color="#252D3D",
            text_color=COLORS["text_muted"], height=36, width=220,
            corner_radius=12, command=self._on_save
        )
        save_btn.pack(padx=20, pady=(0, 16))

        # Classification badge area
        ctk.CTkLabel(parent, text="─── Classification ───",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["text_muted"]).pack(pady=(8, 4), padx=20)
        self._class_label = ctk.CTkLabel(
            parent, text="─",
            font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self._class_label.pack(pady=(4, 8), padx=20)

        # AHA classification reference
        ctk.CTkLabel(parent,
                     text="AHA 2017 Guidelines",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=COLORS["text_muted"]).pack(pady=(12, 4), padx=12, anchor='w')
        ref_text = (
            "  < 120/80     Normal\n"
            "  < 130/80     Elevated\n"
            "  < 140/90     HTN Stage 1\n"
            "  ≥ 140/90     HTN Stage 2\n"
            "  > 180/120    HTN Crisis"
        )
        ctk.CTkLabel(parent, text=ref_text,
                     font=ctk.CTkFont("Courier New", 9),
                     text_color=COLORS["text_muted"],
                     justify='left').pack(padx=12, pady=(0, 12))

    def _make_slider(self, parent, label, from_, to, default):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["text_primary"]).pack(pady=(4, 2), padx=20, anchor='w')
        var = tk.DoubleVar(value=default)
        val_label = ctk.CTkLabel(parent, text=str(int(default)),
                                  font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
                                  text_color=COLORS["accent_teal"])
        val_label.pack(padx=20, anchor='e', pady=(0, 2))
        slider = ctk.CTkSlider(parent, from_=from_, to=to, variable=var, width=220,
                                button_color=COLORS["accent_blue"],
                                progress_color=COLORS["accent_blue"])
        slider.pack(padx=20, pady=(0, 8))

        def on_change(v):
            val_label.configure(text=str(int(float(v))))
        slider.configure(command=on_change)
        # Store reference on slider
        slider._val_var = var
        return slider

    def _build_metrics(self, parent):
        metrics_row = ctk.CTkFrame(parent, fg_color="transparent")
        metrics_row.pack(fill='x', pady=(0, 12))

        self._card_sbp = MetricCard(metrics_row, "Systolic",  "mmHg",
                                     COLORS["accent_red"])
        self._card_sbp.pack(side='left', expand=True, fill='both', padx=(0, 8))

        self._card_dbp = MetricCard(metrics_row, "Diastolic", "mmHg",
                                     COLORS["accent_blue"])
        self._card_dbp.pack(side='left', expand=True, fill='both', padx=(0, 8))

        self._card_map = MetricCard(metrics_row, "MAP",       "mmHg",
                                     COLORS["accent_orange"])
        self._card_map.pack(side='left', expand=True, fill='both', padx=(0, 8))

        self._card_hr  = MetricCard(metrics_row, "Heart Rate", "BPM",
                                     COLORS["accent_teal"])
        self._card_hr.pack(side='left', expand=True, fill='both')

    def _build_waveform(self, parent):
        self._waveform = WaveformPanel(parent)
        self._waveform.pack(fill='both', expand=True)

    def _build_bottom_bar(self):
        bottom = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                               height=44, corner_radius=0)
        bottom.pack(fill='x', side='bottom')
        bottom.pack_propagate(False)

        self._status = StatusBadge(bottom)
        self._status.pack(side='left', padx=20)

        version = ctk.CTkLabel(bottom, text="CuffnCode v1.0  ·  Student Embedded Control & AI Fest",
                                font=ctk.CTkFont("Segoe UI", 10),
                                text_color=COLORS["text_muted"])
        version.pack(side='right', padx=20)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _on_start(self):
        if self._sim_running:
            return
        self._waveform.clear()
        self._all_t.clear()
        self._all_p.clear()
        self._all_phase.clear()
        self._logger.clear()
        self._last_result = None
        self._update_cards(None)
        self._class_label.configure(text="─", text_color=COLORS["text_muted"])

        self._start_btn.configure(state='disabled')
        self._stop_btn.configure(state='normal')
        self._sim_running = True

        mode = self._mode_var.get()
        if mode == "Simulation":
            self._status.set_status("Simulating")
            self._sim_thread = threading.Thread(
                target=self._run_simulation, daemon=True
            )
            self._sim_thread.start()
        else:
            self._status.set_status("Inflating")
            # Hardware mode: would start serial acquisition here
            self._show_error("Hardware mode: connect your Arduino and select the correct COM port.")

    def _on_stop(self):
        self._sim_running = False
        self._status.set_status("Idle")
        self._start_btn.configure(state='normal')
        self._stop_btn.configure(state='disabled')

    def _on_save(self):
        if not self._all_t:
            self._show_error("No recording to save — run a measurement first.")
            return
        self._logger.log_samples_bulk(self._all_t, self._all_p, self._all_phase)
        wf_path = self._logger.save_waveform()
        msg = f"Waveform saved to:\n{wf_path}"
        if self._last_result and self._last_result.valid:
            res_path = self._logger.save_result(self._last_result)
            msg += f"\nResult saved to:\n{res_path}"
        tk.messagebox.showinfo("Saved", msg)

    def _run_simulation(self):
        """Background thread: stream synthetic samples to the UI."""
        config = SimConfig(
            target_sbp=self._sbp_slider._val_var.get(),
            target_dbp=self._dbp_slider._val_var.get(),
            heart_rate=self._hr_slider._val_var.get(),
            sample_rate=SAMPLE_RATE,
        )
        batch_size = int(SAMPLE_RATE * 0.1)  # 100 ms of data per batch
        batch_t, batch_p, batch_phase = [], [], []
        phase_prev = ""

        for t, p, phase in generate_waveform(config):
            if not self._sim_running:
                break
            batch_t.append(t)
            batch_p.append(p)
            batch_phase.append(phase)

            # Update status on phase transitions
            if phase != phase_prev:
                phase_prev = phase
                status_map = {
                    "inflate": "Inflating",
                    "plateau": "Simulating",
                    "deflate": "Deflating",
                }
                self.after(0, self._status.set_status,
                           status_map.get(phase, "Simulating"))

            if len(batch_t) >= batch_size:
                # Compute filtered signals
                t_arr = np.array(batch_t)
                p_arr = np.array(batch_p)

                self._all_t.extend(batch_t)
                self._all_p.extend(batch_p)
                self._all_phase.extend(batch_phase)

                # Compute DC and oscillation for visualization
                dc, osc = None, None
                if len(self._all_p) > int(SAMPLE_RATE * 2):
                    all_p_arr = np.array(self._all_p)
                    try:
                        dc_full = lowpass_filter(all_p_arr, SAMPLE_RATE, cutoff=0.3)
                        osc_full = bandpass_filter(all_p_arr, SAMPLE_RATE, 0.5, 8.0)
                        dc = dc_full[-len(batch_t):]
                        osc = osc_full[-len(batch_t):]
                    except Exception:
                        pass

                self.after(0, self._waveform.add_samples, t_arr, p_arr, dc, osc)
                batch_t, batch_p, batch_phase = [], [], []
                time.sleep(0.08)  # ~80 ms per batch = ~real-time

        # Measurement complete — run algorithm
        if self._all_t:
            self.after(0, self._status.set_status, "Processing")
            self.after(200, self._compute_and_display_result)

    def _compute_and_display_result(self):
        """Run BP algorithm on collected data and update display."""
        t_arr = np.array(self._all_t)
        p_arr = np.array(self._all_p)
        result = compute_bp(t_arr, p_arr, fs=SAMPLE_RATE,
                            phase_arr=self._all_phase)
        self._last_result = result
        self._update_cards(result)
        self._status.set_status("Done" if result.valid else "Error")
        self._start_btn.configure(state='normal')
        self._stop_btn.configure(state='disabled')
        self._sim_running = False

    def _update_cards(self, result: BPResult = None):
        if result is None or not result.valid:
            for card in (self._card_sbp, self._card_dbp,
                         self._card_map, self._card_hr):
                card.set_value(0)
            return
        self._card_sbp.set_value(result.sbp)
        self._card_dbp.set_value(result.dbp)
        self._card_map.set_value(result.map_val)
        self._card_hr.set_value(result.heart_rate)
        # Flash and update classification
        self._card_sbp.flash(result.classification_color)
        self._card_dbp.flash(result.classification_color)
        self._class_label.configure(
            text=result.classification,
            text_color=result.classification_color
        )

    def _start_refresh_loop(self):
        """Periodically refresh the waveform plot."""
        self._waveform.refresh()
        self._update_clock()
        self.after(self._refresh_rate_ms, self._start_refresh_loop)

    def _update_clock(self):
        now = datetime.now().strftime("%A, %d %B %Y  %H:%M:%S")
        self._time_label.configure(text=now)

    def _show_error(self, msg: str):
        self._status.set_status("Error")
        tk.messagebox.showerror("CuffnCode Error", msg)
        self._start_btn.configure(state='normal')
        self._stop_btn.configure(state='disabled')
        self._sim_running = False
