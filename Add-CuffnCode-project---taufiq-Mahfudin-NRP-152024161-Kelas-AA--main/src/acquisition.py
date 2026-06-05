"""
CuffnCode — Hardware Serial Acquisition Module
Handles communication with the Arduino/microcontroller over USB serial.

Expected Arduino output format (CSV per line):
  timestamp_ms,pressure_raw,valve1_state,valve2_state,pump_state
"""

import serial
import serial.tools.list_ports
import threading
import queue
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ADC calibration constants (adjust for your sensor)
ADC_VREF = 5.0       # Volts
ADC_BITS = 10        # Arduino Uno = 10-bit ADC
SENSOR_VMIN = 0.2    # V at 0 mmHg (MPX5050 offset)
SENSOR_VMAX = 4.7    # V at full scale
SENSOR_PMAX = 50.0   # kPa full scale (MPX5050)
KPA_TO_MMHG = 7.5006 # 1 kPa = 7.5006 mmHg


def adc_to_mmhg(adc_raw: int) -> float:
    """Convert raw ADC value to pressure in mmHg."""
    voltage = (adc_raw / (2 ** ADC_BITS - 1)) * ADC_VREF
    kpa = ((voltage - SENSOR_VMIN) / (SENSOR_VMAX - SENSOR_VMIN)) * SENSOR_PMAX
    return max(0.0, kpa * KPA_TO_MMHG)


def list_serial_ports() -> list[str]:
    """Return available serial port names."""
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


class SerialAcquisition:
    """
    Threaded serial data reader for real-time acquisition.
    Puts parsed (time, pressure_mmhg) tuples into a thread-safe queue.
    """

    def __init__(self, port: str, baudrate: int = 115200,
                 on_data: Optional[Callable] = None):
        self.port = port
        self.baudrate = baudrate
        self.on_data = on_data
        self._ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.data_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._start_time: float = 0.0

    def connect(self) -> bool:
        """Open the serial port. Returns True on success."""
        try:
            self._ser = serial.Serial(
                self.port, self.baudrate,
                timeout=1.0, write_timeout=1.0
            )
            time.sleep(2.0)  # Wait for Arduino reset
            self._ser.reset_input_buffer()
            logger.info(f"Connected to {self.port} @ {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"Serial connect failed: {e}")
            return False

    def disconnect(self):
        """Stop reading and close port."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._ser and self._ser.is_open:
            self._ser.close()
        logger.info("Serial port closed")

    def start_acquisition(self):
        """Start background reading thread."""
        if not self._ser or not self._ser.is_open:
            raise RuntimeError("Not connected — call connect() first")
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop_acquisition(self):
        """Stop background reading."""
        self._running = False

    def send_command(self, cmd: str):
        """Send a command string to the Arduino (e.g., 'INFLATE', 'DEFLATE')."""
        if self._ser and self._ser.is_open:
            self._ser.write((cmd + '\n').encode('utf-8'))

    def _read_loop(self):
        """Background thread: read lines and parse sensor data."""
        while self._running:
            try:
                line = self._ser.readline().decode('utf-8', errors='ignore').strip()
                if not line or line.startswith('#'):
                    continue  # skip comments/empty
                parts = line.split(',')
                if len(parts) >= 2:
                    adc_raw = int(parts[1])
                    pressure = adc_to_mmhg(adc_raw)
                    t = time.time() - self._start_time
                    sample = (t, pressure)
                    if not self.data_queue.full():
                        self.data_queue.put(sample)
                    if self.on_data:
                        self.on_data(t, pressure)
            except (ValueError, IndexError):
                pass  # malformed line
            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                self._running = False

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open
