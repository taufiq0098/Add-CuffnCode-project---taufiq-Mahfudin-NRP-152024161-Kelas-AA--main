# 💉 CuffnCode

> A retrofitted blood pressure measurement system for teaching and research.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Arduino%20%2F%20RPi-orange)](arduino/)
[![Docs](https://img.shields.io/badge/Docs-GitHub%20Pages-blueviolet)](https://student-embedded-control-and-ai-fest.github.io/CuffnCode)

CuffnCode is an open-source, **over-instrumented** blood pressure monitoring platform that combines embedded hardware with a Python-based signal processing and visualization stack. It is designed for:

- 📚 **Teaching** — understand the oscillometric method hands-on
- 🔬 **Research** — test new signal processing and control algorithms
- 🛠️ **Hacking** — extend and retrofit with your own sensors and actuators

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Python Application                     │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  Simulator │  │Signal Processing│  │  BP Algorithm  │  │
│  │ (demo mode)│  │ (filter/peaks) │  │ (oscillometric)│  │
│  └────────────┘  └────────────────┘  └────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │               GUI Dashboard (customtkinter)          │ │
│  │  Live Waveform  │  SBP/DBP/MAP Cards  │  Controls   │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌────────────┐  ┌────────────────┐                       │
│  │   Serial   │  │  Data Logger   │                       │
│  │ Acquisition│  │  (CSV / JSON)  │                       │
│  └────────────┘  └────────────────┘                       │
└──────────────────────────────┬───────────────────────────┘
                               │ USB Serial (115200 baud)
┌──────────────────────────────▼───────────────────────────┐
│                   Arduino Uno / Nano                      │
│  Pin 9  → DC Micro-Pump (PWM via MOSFET)                 │
│  Pin 7  → Solenoid Valve 1 (slow deflate)                │
│  Pin 8  → Solenoid Valve 2 (fast vent)                   │
│  A0     → MPX5050 Pressure Sensor                        │
└──────────────────────────────────────────────────────────┘
```

---

## 🩺 The Oscillometric Method

CuffnCode uses the **oscillometric method** to determine blood pressure non-invasively:

1. **Inflate** the cuff above systolic pressure (no blood flow → no oscillations)
2. **Slowly deflate** — as pressure falls, arterial oscillations appear on the cuff
3. **Peak amplitude** occurs at **Mean Arterial Pressure (MAP)**
4. **SBP** is detected where oscillation amplitude = **45%** of maximum
5. **DBP** is detected where oscillation amplitude = **70%** of maximum

```
Oscillation
Amplitude
    │                  ▲ MAP (peak)
    │               ╱     ╲
    │             ╱         ╲
45% ├- - - - - ╱- - - - - - -╲- - - - - ← SBP threshold
    │         ╱               ╲
70% ├- - - ╱- - - - - - - - - -╲- - - - ← DBP threshold (of peak)
    │     ╱                     ╲
    │   ╱                         ╲
    └──────────────────────────────────→ Cuff Pressure
       ↑ SBP                    ↑ DBP
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/Student-Embedded-Control-and-AI-Fest/CuffnCode.git
cd CuffnCode
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python main.py
```

The GUI will open. Click **▶ Start Measurement** to run a simulation.

---

## 🔌 Hardware Setup

### Bill of Materials

| Component              | Part Number / Spec          | Qty |
|------------------------|-----------------------------|-----|
| Microcontroller        | Arduino Uno / Nano          | 1   |
| DC Micro Air Pump      | 3–6V, ~100 mL/min           | 1   |
| Solenoid Valve         | 3V NC (Normally Closed)     | 2   |
| Pressure Sensor        | Freescale MPX5050 (0–50 kPa)| 1   |
| N-Channel MOSFET       | 2N7000 or IRLZ44N           | 3   |
| Flyback Diode          | 1N4007                      | 3   |
| Blood Pressure Cuff    | Standard adult cuff + tubing| 1   |
| Power Supply           | 5V 2A regulated             | 1   |

### Wiring Diagram

```
Arduino                 MOSFET Gate         Load
─────────────────────────────────────────────────
Pin 9  ── 100Ω ──┬── Gate (IRLZ44N) ── Pump (5V)
                 └── 10kΩ ── GND
Pin 7  ── 100Ω ──── Gate ── Solenoid Valve 1
Pin 8  ── 100Ω ──── Gate ── Solenoid Valve 2
A0     ──────────── MPX5050 Vout
                    (Vcc=5V, GND, decoupling cap 100nF)
```

### Upload Firmware

1. Open `arduino/CuffnCode/CuffnCode.ino` in Arduino IDE
2. Select **Tools → Board: Arduino Uno**
3. Select the correct **COM port**
4. Click **Upload**

---

## 💻 Software Reference

### Project Structure

```
CuffnCode/
├── main.py                     # Entry point
├── requirements.txt
├── README.md
│
├── src/
│   ├── simulator.py            # Synthetic waveform generator
│   ├── signal_processing.py    # Bandpass filter, envelope, peaks
│   ├── bp_algorithm.py         # Oscillometric BP computation
│   ├── acquisition.py          # Serial hardware interface
│   └── data_logger.py          # CSV/JSON data saving
│
├── gui/
│   └── dashboard.py            # Main GUI (customtkinter + matplotlib)
│
├── arduino/
│   └── CuffnCode/
│       └── CuffnCode.ino       # Arduino firmware
│
├── tests/
│   ├── test_signal_processing.py
│   └── test_bp_algorithm.py
│
└── data/
    └── recordings/             # Saved measurement sessions
```

### Running Tests

```bash
pip install pytest
pytest tests/ -v
```

### Serial Protocol

The Arduino sends CSV lines at 100 Hz:

```
timestamp_ms,adc_raw,pump_state,valve1_state,valve2_state
1234,512,1,0,0
1244,515,1,0,0
...
```

Python commands to Arduino:

| Command   | Description                          |
|-----------|--------------------------------------|
| `INFLATE` | Start pump, inflate to target        |
| `DEFLATE` | Controlled slow deflation            |
| `VENT`    | Emergency fast pressure release      |
| `STOP`    | Stop all actuators immediately       |
| `STATUS`  | Query current ADC and state          |

---

## 📊 Signal Processing Pipeline

```
Raw Pressure Signal
        │
        ▼
   Lowpass Filter (0.3 Hz)
        │                      → DC Trend (cuff pressure envelope)
        │
   Bandpass Filter (0.5–8 Hz)
        │                      → Oscillometric Oscillations
        │
   Envelope Extraction (|osc| + Savitzky-Golay)
        │
   Peak Detection (scipy.find_peaks)
        │
   Oscillometric Ratio Thresholds
        │
        ▼
  SBP / DBP / MAP / HR
```

---

## 🏷️ BP Classification (AHA 2017)

| Category              | Systolic       | Diastolic    |
|-----------------------|----------------|--------------|
| Normal                | < 120 mmHg     | < 80 mmHg    |
| Elevated              | 120–129 mmHg   | < 80 mmHg    |
| Hypertension Stage 1  | 130–139 mmHg   | 80–89 mmHg   |
| Hypertension Stage 2  | ≥ 140 mmHg     | ≥ 90 mmHg    |
| Hypertensive Crisis   | > 180 mmHg     | > 120 mmHg   |

---

## 🔭 Future Work

- [ ] PID controller for closed-loop deflation rate
- [ ] Kalman filter for noise-robust oscillation detection
- [ ] Raspberry Pi port (SPI pressure sensor)
- [ ] BLE / WiFi wireless cuff interface
- [ ] Machine learning BP classifier (LSTM on raw PPG)
- [ ] Multi-patient database with trend visualization

---

## 👥 Team

**Student Embedded Control and AI Fest**
- Project Lead & Algorithm: [Team Member]
- Hardware & Firmware: [Team Member]
- GUI & Data Analysis: [Team Member]
- Documentation: [Team Member]

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📚 References

1. Drzewiecki, G. et al., "Noninvasive blood pressure recording and the genesis of Korotkoff sound," *Handbook of Bioengineering*, 1987.
2. Geddes, L.A., et al., "Characterization of the oscillometric method for measuring indirect blood pressure," *Annals of Biomedical Engineering*, 1982.
3. American Heart Association (AHA), "2017 ACC/AHA High Blood Pressure Guidelines."
4. Freescale Semiconductor, "MPX5050 Series Datasheet," 2013.
