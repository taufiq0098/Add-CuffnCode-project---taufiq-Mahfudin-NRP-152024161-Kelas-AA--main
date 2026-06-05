# CuffnCode — Data Directory

This folder stores recorded measurement sessions.

## Structure

```
data/
└── recordings/
    ├── waveform_YYYYMMDD_HHMMSS.csv    ← Raw pressure waveform
    └── result_YYYYMMDD_HHMMSS.json     ← BP measurement result
```

## CSV Format

| Column          | Description                    |
|-----------------|--------------------------------|
| `time_s`        | Time since measurement start   |
| `pressure_mmhg` | Cuff pressure in mmHg          |
| `phase`         | inflate / plateau / deflate    |

## JSON Format

```json
{
  "session_id": "20260605_123456",
  "timestamp": "2026-06-05T12:34:56",
  "sbp_mmhg": 120.0,
  "dbp_mmhg": 80.0,
  "map_mmhg": 93.3,
  "heart_rate_bpm": 72.0,
  "classification": "Normal",
  "valid": true
}
```
