# Rigol Capture — Project Handover

Last reviewed: 2026-11-15
Repository: `FLRHW/Rigol_capture`

## Purpose
Standalone, standard-library-only Python 3 exporter for stopped Rigol DS1054Z/DS1000Z waveform data over SCPI TCP. The tool exports CSV for subsequent analysis. It is independent of the CPX400DP application and does not synchronise captures to its timeline.

## Repository layout
- `rigol_ds1054z_capture.py` — CLI, TCP/SCPI transport, waveform block retrieval, conversion and streaming CSV export.
- `test_rigol_capture.py` — simulated instrument/SCPI tests via `FakeSocket`.
- `test_rigol_decimation.py` — decimation/index boundary tests.
- `README.txt` — v2 RAW/NORMAL usage and workflow.
- `README_v2_1.txt` — v2.1 stride-decimation usage and limitations.
- `docs/PROJECT_HANDOVER.md` — durable architecture and decisions.
- `docs/SESSION_STATE.md` — current revision, evidence, defects and next steps.

## Implementation architecture (source-reviewed)
1. CLI `main()` uses `argparse` with required `--host`. Defaults: TCP port 5555, channels 2 and 4, mode `raw`, `rigol_scope.csv`, 20 s timeout, 250000-point chunk, decimation factor 1. `--interface` is optional.
2. `Rigol` opens a TCP socket. On Linux it can bind to a specific network device via `SO_BINDTODEVICE`; otherwise it uses `socket.create_connection`. Commands are ASCII and LF-terminated. `get()` buffers incoming bytes, `readline()` handles text responses, `block()` reads IEEE 488.2 definite-length binary blocks.
3. `*IDN?` checks that the returned identity contains `RIGOL`. RAW mode queries `:TRIG:STAT?` and only accepts STOP/STOPPED. The program does **not** issue `:RUN` or `:STOP`; the user prepares the acquisition on the oscilloscope.
4. Per channel: `:WAV:SOUR CHANn`, `:WAV:MODE RAW` or `NORM`, `:WAV:FORM BYTE`, `:WAV:PRE?`. Preamble parser requires 10 fields, BYTE format, requested mode, positive x increment and nominal point count <=24,000,000.
5. Both RAW and NORMAL transfer loops explicitly set inclusive, 1-based `:WAV:STAR` and `:WAV:STOP` ranges before `:WAV:DATA?` in chunks <=250000. Unexpected block sizes raise errors, including a short NORMAL response. This fixes the previous dependence on stale instrument readout ranges.
6. Data conversion: zero-based `sample_index`; `scope_time_s = x_origin + (index - x_reference)*x_increment`; `voltage_v = (byte - y_origin - y_reference)*y_increment`. The formulas use the returned preamble; confirm scaling with real signals.
7. CSV is written incrementally, channel by channel, with `capture_utc,scope_idn,scope_channel,sample_index,scope_time_s,voltage_v`. UTC capture timestamp is a PC-side export time, **not** a shared acquisition timestamp. File is not atomic; on error partial output may remain.
8. `--decimate N` retains samples where original zero-based index modulo N equals zero across chunk boundaries. **All samples are still downloaded**; only output rows are reduced. This is stride selection without anti-alias filtering and may miss short pulses.

## Current implementation vs verification
**Implemented in source:** CLI, TCP transport, RAW and NORMAL modes, stopped check for RAW, BYTE preamble parsing, chunking, CSV scaling, streaming output, decimation and basic error guards.

**Offline-tested:** Previously passing isolated mocked-suite run was recorded for the earlier revision (12 executions, 7 unique tests). New NORMAL range/short-block regression tests have been added since that run and **have not yet been executed** against the revised source.

**Hardware-validated:** Ethernet reachability; corrected two-channel NORMAL CLI (1200 points each) with subsequent uploaded CSV structure/index/timestamp inspection; and two-channel RAW CLI transferring 6,000,000 samples/channel in 250,000-point chunks, all reported complete on 2026-11-15. NORMAL CSV has 2400 rows; CH2/CH4 indices 0..1199 and time -0.98..11.01 s at 0.01 s intervals. Full RAW CSV and physical voltage/time calibration remain unverified.

**Planned/future investigation:** Physical validation, enhanced reliability and regression cases, documented dependencies/platform considerations, and any later integration or synchronization work (not currently a requirement).

## Usage
```bash
python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 4 --mode raw --output rigol_raw.csv
python3 rigol_ds1054z_capture.py --host 169.254.179.79 --channels 2 4 --mode normal --output rigol_screen.csv
python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 --mode raw --decimate 500 --output rigol_reduced.csv
python3 -m unittest discover -q
```
Addresses/interfaces are examples from the developer's setup, not proof of current connectivity.

## Historical observations / safety
- Rigol DS1054Z connected in separate experiments using link-local IP `169.254.179.79`, Linux interface `enp3s0f1` and PC address `169.254.179.80`. Confirm actual routing before testing.
- Separate hardware investigation: CH3 voltage at approximately 25 V DC was observed slowly rising/drifting while CH2 behaved normally; unresolved and not evidence of capture-tool behavior.
- Confirm input limits, probe/attenuator settings, shared-earth grounding and safe signal sources before tests; do not rely on software protection.
- RAW requires the instrument already stopped; avoid modifying acquisition conditions while downloading and preserve original captures until CSV integrity is checked.
- A decimated waveform cannot establish the absence of short transients; use full-resolution data for glitches.

## Known engineering limits / code-review follow-up
- NORMAL CLI transferred 1200 samples/channel; uploaded CSV verified 2400 rows, contiguous index/time progression. RAW CLI transferred 6M samples/channel in 24 chunks per channel (250k each) at reported 2 us/sample, but raw CSV itself has not been inspected. Analog accuracy and other preamble variations remain unverified.
- 2026-11-15 hardware finding: before the fix, NORMAL CH2/CH4 exports returned one sample each. Diagnostic showed CH2 retained `:WAV:STAR? = 5750001`, `:WAV:STOP? = 6000000`; setting `:WAV:STAR 1`, `:WAV:STOP 1200` allowed 1200 samples on both channels. Fixed in committed source by always setting ranges. Full CLI re-test subsequently succeeded with 1200 samples/channel; analog/time accuracy remains unverified.
- The CSV records export timestamp and per-channel scope-relative times; channels are serialized during transfer, and no cross-instrument time alignment exists.
- RAW CSV from 12 million samples (CH2+CH4) was reported over 1 GB. Existing `--decimate N` reduces saved CSV rows while still downloading all points; e.g. N=500 gives 12000 rows/channel, 1 ms spacing at the reported 2 us original interval. This is point-stride decimation that may miss narrow events. Consider future min/max-envelope export for visual fidelity. Partial CSV may remain on transfer failure.
- Linux-only interface binding feature requires compatible privileges/kernel; test the intended environment.
- The nominal 24M-point bound is a guard, not a guarantee of scope memory depth under every channel configuration.

## Maintenance requirements
Update this file after architecture/requirements/safety decisions and important hardware findings. Maintain `docs/SESSION_STATE.md` with actual branch/commit, what was implemented, test command/results, hardware conditions, open issues and next actions. Always distinguish implemented, offline-tested, hardware-validated and planned; compare documentation against committed source before ending development sessions. Do not rely only on conversation history.
