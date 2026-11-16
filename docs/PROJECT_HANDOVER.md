# Rigol Capture — Project Handover

Last reviewed: 2026-11-16
Repository: `FLRHW/Rigol_capture`

## 2026-11-16 — Intermittent short SCPI waveform block, independent DSRemote troubleshooting

**Live user capture observation:** Rigol DS1054Z firmware `00.04.04.SP4`
identified over Ethernet on automatic system route; CH2 captured 940/940 RAW
points, decimation=1, with full CSV rows at 0.002 s original spacing.
CH4's preamble advertised 1,200 points, but a `:WAV:DATA?` request for the
1-based range 1..1200 returned an **entire IEEE488.2 binary block of only
128 BYTE samples**. The exporter raised:
`ValueError: CH4: requested 1200 points at 1, got 128`.
No evidence of TCP recv truncation: `Rigol.block()` reads the length
advertised in the block header and then that number of bytes. The
scope may have a transient/limited waveform buffer or returned a different
readout than the preamble describes; root cause is **not yet proven**.

**Context:** Separate DSRemote program connected and read waveform for a
few seconds after repairing a lost Rigol /32 route, then repeatedly failed
at `screen_thread.cpp line 783` while the physical scope continued
operating normally. DSRemote's failure was also reproduced with the
CPX400DP GUI closed. Independent waveform capture can succeed in
small batches, so network reachability alone does not validate ongoing
waveform transfers.

**Safe code change on main:** `rigol_ds1054z_capture.py` now reports
the channel, mode, requested inclusive SCPI point range, preamble count
and returned binary block length in the short-block exception. It
explicitly refuses to fabricate missing samples or silently accept
a truncated capture. Test `test_rigol_capture.py` adds a mocked
1200-vs-128 failure and updates the existing NORMAL short-block
assertion. Actual waveform acquisition/CSV scaling and :RUN/:STOP
safeguards have **not been modified**.

**Next controlled tests:** with both Ethernet routes checked and
DSRemote disconnected, capture CH4 alone in RAW mode with advanced
chunk size **128** and decimation 1; then CH2+CH4 using the same
chunk size, watching for short blocks. Capture again in NORMAL mode
if RAW remains inconsistent. Do not restart or alter the oscilloscope
acquisition during an active RAW export. Record scope STOP state,
channel display enable, returned point counts and exact errors.
Small-chunk success is evidence about the transfer window, **not**
proof of DSRemote root cause or indefinite transport stability.
An exception can leave a partially written CSV; preserve any
complete prior capture under a different filename.

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



## 2026-11-15 RAW stride-decimation hardware result
A stopped DS1054Z with CH2 and CH4 enabled completed a RAW capture with `--decimate 500`. Each channel downloaded 6,000,000 points in 250,000-point chunks and wrote 12,000 CSV rows, reporting original spacing 2 microseconds and saved spacing 1 millisecond, without console errors. The CSV itself has not been inspected, so per-row indices, time/voltage values, and analogue accuracy remain unvalidated.

## Requested next revision — desktop GUI (planned, not implemented)
Provide a simple Kubuntu-friendly desktop front end with host/IP, network interface, channel selection, RAW/NORMAL mode, decimation factor, output path, capture progress, error reporting, and sensible safeguards. Preserve CLI behavior and the current instrument stop-state protection; do not start or stop the acquisition implicitly. Tkinter is one suitable lightweight approach; choice and details to be confirmed during implementation. A future optional peak-preserving downsampling mode may be considered, distinct from the existing stride decimation.


## 2026-11-15 uploaded decimated CSV inspection
The supplied `test2_raw_decimated(1).csv` was inspected programmatically (2,808,516 bytes). Exactly 24,000 data rows, 12,000 each for CH2 and CH4. Both channels have zero missing/duplicate steps: original sample indices 0 through 5,999,500, in increments of 500; time -0.98 through 11.019 seconds, increments of 0.001 s. CH2 voltages range 0.0 to 8.03578125 V, CH4 1.84570323 to 7.99804733 V. Each row includes the same Rigol DS1054Z instrument identity and UTC export timestamp; the values are not externally calibrated. File structure and progression **validated**, absolute voltage accuracy **not validated**.

## GUI dependency decision
Reuse the same Qt bindings already supported by the CPX400DP controller: attempt `PySide6` first, fall back to `PyQt5`; retain the CLI capture module as a standard-library-only independent backend. CPX400DP `scripts/cpx400dp_gui.py` on `dev` uses QProcess/QThread, QSettings, QFileDialog, QComboBox, QCheckBox, QProgressBar. The Rigol GUI should use these patterns, without a separate GUI toolkit. Running in the same Python environment avoids additional GUI dependency installation. **GUI implemented in source as an initial release, awaiting offline execution and hardware GUI validation.**


## First Qt GUI implementation (2026-11-15)
- `rigol_ds1054z_gui.py` is a stand-alone Qt frontend using the same PySide6-first / PyQt5-fallback import strategy as CPX400DP. Launch with `python3 rigol_ds1054z_gui.py` in the same interpreter/environment as the existing PSU app.
- `rigol_gui_core.py` is a standard-library-only parameter validator/CLI argument builder; `test_rigol_gui_core.py` exercises input validation without Qt.
- GUI fields: host, interface, SCPI port, socket timeout, channel selection, RAW/NORMAL, stride decimation, transfer chunk size and CSV output chooser. QSettings persists values locally.
- Uses QProcess to invoke existing `rigol_ds1054z_capture.py` with unbuffered Python stdout, merges console streams and parses `CHn: transferred/total points` progress. The backend retains exclusive socket ownership and all RUN/STOP protection.
- Cancel terminates the subprocess and may leave a partial CSV. Closing the window while busy is blocked; repeat export to an existing file asks for overwrite confirmation. Errors are surfaced from CLI stderr/stdout. No waveform plot or actual scope control.
- Source-only implementation: GUI not launched on Kubuntu, no Qt headless smoke test, and no hardware GUI capture validated at this point. CI workflow `.github/workflows/offline-tests.yml` added for compileall and unit tests; success must be checked separately.
- Previous `test_normal_mode` assertion (which contradicted the NORMAL range fix) was aligned with the corrected code; decimation tests no longer import an unrelated `Tests` class that caused duplicate discovery.
- New `README.md` describes GUI/CLI startup and `.gitignore` excludes generated `captures/`, `test*.csv`, Python bytecode.


## Automatic interface selection (2026-11-16)
- The Qt GUI now defaults to **automatic interface selection** and standard Rigol SCPI TCP port 5555. No network interface needs to be entered in normal use. The previous fixed `QSettings` interface value is deliberately ignored on migration; only an explicitly re-entered advanced manual override is preserved.
- `rigol_network.py` is a standard-library Linux helper. It first attempts a socket with system routing, then the device identified by `ip -4 route get`, then other active IPv4 interfaces reported by `ip -o -4 addr show up`. Each attempted path is opened for a short `*IDN?` query; only an identity containing `RIGOL` is accepted. Failures are reported without changing host networking configuration. The probe is run in a Qt QThread before starting the normal QProcess capture engine.
- **Advanced connection settings** is initially collapsed; it contains an optional interface override, TCP port, socket timeout and chunk size. Overrides are not attempted silently in fallback mode: entering one means only that interface is tried. No multicast/broadcast scanning and no host-address discovery were implemented; the scope IP/hostname is still user-provided.
- The GUI's pre-capture identity check uses a short-lived separate SCPI socket which is closed before the transfer starts. The original CLI backend remains unchanged, owns the transfer socket, and continues to enforce the RAW stopped-acquisition check. No implicit RUN/STOP commands are issued.
- New `test_rigol_network.py` covers route parsing, active IPv4 interface parsing, candidate precedence, fallback and manual override behaviour using mocks. CI compile step includes the new module. **These are source-implemented changes; actual regression/CI and hardware testing must be independently verified.**
- Automatic probing may fail if link-local routes/addresses are misconfigured, `ip` is absent, or a local firewall/kernel prevents access. The GUI provides an explicit advanced manual interface field for such cases. Port 5555 is a known default, not discovered from the instrument.

## Maintenance requirements
Update this file after architecture/requirements/safety decisions and important hardware findings. Maintain `docs/SESSION_STATE.md` with actual branch/commit, what was implemented, test command/results, hardware conditions, open issues and next actions. Always distinguish implemented, offline-tested, hardware-validated and planned; compare documentation against committed source before ending development sessions. Do not rely only on conversation history.
