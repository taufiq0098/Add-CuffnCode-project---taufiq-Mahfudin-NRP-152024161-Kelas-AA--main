/*
 * PulseTrack Pro — Arduino Firmware
 * =================================
 * Smart Blood Pressure Monitoring System
 *
 * Hardware:
 *   - DC Micro-pump (inflate) → pin 9 (PWM via MOSFET)
 *   - Solenoid Valve 1 (slow deflate) → pin 7
 *   - Solenoid Valve 2 (fast vent) → pin 8
 *   - Pressure Sensor MPX5050 → A0
 *   - Status LED → pin 13
 *
 * Serial protocol (115200 baud):
 *   Output: "timestamp_ms,adc_raw,pump,valve1,valve2\n"
 *   Input commands:
 *     INFLATE  — start inflating to target
 *     DEFLATE  — controlled deflation
 *     VENT     — fast release (emergency)
 *     STOP     — stop all actuators
 *     STATUS   — query current state
 *
 *Author: Taufiq Mahfudin — NRP 152024161
 */

// ── Pin Definitions ──────────────────────────────────────────────────────────
const int PIN_PUMP    = 9;    // PWM output to pump MOSFET gate
const int PIN_VALVE1  = 7;    // Solenoid valve 1 (slow deflate)
const int PIN_VALVE2  = 8;    // Solenoid valve 2 (fast vent)
const int PIN_SENSOR  = A0;   // Pressure sensor analog input
const int PIN_LED     = 13;   // Status LED

// ── Configuration ─────────────────────────────────────────────────────────────
const int   SAMPLE_INTERVAL_MS  = 10;     // 100 Hz sampling
const int   INFLATE_TARGET_ADC  = 700;    // ~180 mmHg inflate target (tune for sensor)
const int   SAFETY_MAX_ADC      = 750;    // Emergency cutoff
const int   PUMP_PWM            = 200;    // Pump speed 0–255
const float DEFLATE_RATE_MS     = 10;     // ms between deflate steps
const int   DEFLATE_STEP_MS     = 50;     // open valve for 50 ms per step

// ── State Machine ─────────────────────────────────────────────────────────────
enum State { IDLE, INFLATING, DEFLATING, VENTING, ERROR_STATE };
State currentState = IDLE;

unsigned long lastSampleTime = 0;
unsigned long lastDeflateTime = 0;
bool valve1Open = false;
bool valve2Open = false;
bool pumpOn = false;

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(PIN_PUMP,   OUTPUT);
  pinMode(PIN_VALVE1, OUTPUT);
  pinMode(PIN_VALVE2, OUTPUT);
  pinMode(PIN_LED,    OUTPUT);

  stopAll();
  Serial.println("PulseTrack Pro v2.0 Ready");
  Serial.println("# Developed by Taufiq Mahfudin");
  Serial.println("# NRP 152024161 - Kelas AA");
  Serial.println("# Commands: START, DEFLATE, VENT, STOP, STATUS");

// ── Main Loop ─────────────────────────────────────────────────────────────────
void loop() {
  handleSerial();
  runStateMachine();
  sampleAndSend();
}

// ── Serial Command Handler ────────────────────────────────────────────────────
void handleSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "INFLATE") {
    currentState = INFLATING;
    Serial.println("# State: INFLATING");
  } else if (cmd == "DEFLATE") {
    currentState = DEFLATING;
    Serial.println("# State: DEFLATING");
    stopPump();
  } else if (cmd == "VENT") {
    currentState = VENTING;
    Serial.println("# State: VENTING");
    emergencyVent();
  } else if (cmd == "STOP") {
    currentState = IDLE;
    stopAll();
    Serial.println("# State: IDLE");
  } else if (cmd == "STATUS") {
    int adc = analogRead(PIN_SENSOR);
    Serial.print("# ADC="); Serial.print(adc);
    Serial.print(" State="); Serial.println(stateToString());
  } else {
    Serial.print("# Unknown command: "); Serial.println(cmd);
  }
}

// ── State Machine ─────────────────────────────────────────────────────────────
void runStateMachine() {
  int adc = analogRead(PIN_SENSOR);

  switch (currentState) {
    case INFLATING:
      digitalWrite(PIN_LED, HIGH);
      if (adc >= INFLATE_TARGET_ADC) {
        // Target reached — switch to deflating
        stopPump();
        currentState = DEFLATING;
        Serial.println("# Target reached — DEFLATING");
      } else if (adc >= SAFETY_MAX_ADC) {
        // Safety cutoff
        stopAll();
        currentState = ERROR_STATE;
        Serial.println("# ERROR: Safety pressure exceeded!");
      } else {
        startPump();
      }
      break;

    case DEFLATING:
      digitalWrite(PIN_LED, (millis() / 300) % 2);  // slow blink
      // Pulse valve 1 open briefly to allow controlled deflation
      if (millis() - lastDeflateTime > DEFLATE_RATE_MS) {
        openValve1();
        delay(DEFLATE_STEP_MS);
        closeValve1();
        lastDeflateTime = millis();
      }
      if (adc <= 10) {
        // Fully deflated
        closeValve1();
        currentState = IDLE;
        Serial.println("# Deflation complete — IDLE");
        digitalWrite(PIN_LED, LOW);
      }
      break;

    case VENTING:
      openValve2();
      if (adc <= 5) {
        closeValve2();
        currentState = IDLE;
        Serial.println("# Vent complete — IDLE");
      }
      break;

    case ERROR_STATE:
      // Fast blink error indicator
      digitalWrite(PIN_LED, (millis() / 100) % 2);
      emergencyVent();
      break;

    case IDLE:
    default:
      digitalWrite(PIN_LED, LOW);
      stopAll();
      break;
  }
}

// ── Sampling & Transmission ───────────────────────────────────────────────────
void sampleAndSend() {
  unsigned long now = millis();
  if (now - lastSampleTime < SAMPLE_INTERVAL_MS) return;
  lastSampleTime = now;

  int adc = analogRead(PIN_SENSOR);
  // Format: timestamp_ms, adc_raw, pump_state, valve1, valve2
  Serial.print(now);       Serial.print(",");
  Serial.print(adc);       Serial.print(",");
  Serial.print(pumpOn);    Serial.print(",");
  Serial.print(valve1Open);Serial.print(",");
  Serial.println(valve2Open);
}

// ── Actuator Helpers ──────────────────────────────────────────────────────────
void startPump()   { analogWrite(PIN_PUMP, PUMP_PWM); pumpOn = true; }
void stopPump()    { analogWrite(PIN_PUMP, 0);          pumpOn = false; }
void openValve1()  { digitalWrite(PIN_VALVE1, HIGH);    valve1Open = true; }
void closeValve1() { digitalWrite(PIN_VALVE1, LOW);     valve1Open = false; }
void openValve2()  { digitalWrite(PIN_VALVE2, HIGH);    valve2Open = true; }
void closeValve2() { digitalWrite(PIN_VALVE2, LOW);     valve2Open = false; }

void stopAll() {
  stopPump();
  closeValve1();
  closeValve2();
}

void emergencyVent() {
  stopPump();
  closeValve1();
  openValve2();
}

String stateToString() {
  switch (currentState) {
    case IDLE:        return "IDLE";
    case INFLATING:   return "INFLATING";
    case DEFLATING:   return "DEFLATING";
    case VENTING:     return "VENTING";
    case ERROR_STATE: return "ERROR";
    default:          return "UNKNOWN";
  }
}
