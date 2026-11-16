# Rigol Capture — Session State

Last reviewed: 2026-11-15
Repository: `FLRHW/Rigol_capture`
Branch: `main`

## Git revision / synchronization
- Application source reviewed at `dd25ba1` (developer's clean local `main` and `origin/main` at that revision).
- Documentation-only update of `PROJECT_HANDOVER.md`: `e54be4ffaca8171a805566661b2aa22f70f408e3`.
- This `SESSION_STATE.md` update is committed **after** the handover update; the new commit containing this file is the current remote HEAD. Use `git rev-parse HEAD` or GitHub history for its exact SHA after fetching. The application code remains unchanged at the above reviewed revision.
- After these remote documentation commits, the local checkout will need `git pull --ff-only` to synchronize; the previously reported clean status predates these documentation changes.

## Source reviewed on GitHub
- `rigol_ds1054z_capture.py`: CLI, TCP/SCPI transport, RAW and NORMAL waveform reads, BYTE preamble conversion, CSV writer and stride decimation.
- `test_rigol_capture.py`: mock transport, raw chunk ordering, scale and CLI metadata, stopped guard, normal mode and preamble mismatch.
- `test_rigol_decimation.py`: decimation across chunks, original time/index preservation and invalid factor guard.
- `README.txt` and `README_v2_1.txt`: documented usage, scope preparation, and reduction limitations.

## Implemented (reviewed in committed source)
- SCPI TCP socket default port 5555; optional Linux device binding with `--interface`.
- Instrument `*IDN?` sanity check; RAW-mode `:TRIG:STAT?` STOP/STOPPED requirement; does not issue RUN or STOP.
- Per-channel RAW/NORM BYTE export using `:WAV:PRE?`, `:WAV:DATA?`, and 1-based, inclusive RAW chunk start/stop commands up to 250000 samples.
- Preamble-based time/voltage conversion, streaming CSV columns `capture_utc,scope_idn,scope_channel,sample_index,scope_time_s,voltage_v`.
- `--decimate N` saves rows with original index % N == 0 while downloading all points.
- CLI argument validation and basic transfer errors.

## Offline-tested
- **PASS (isolated source-copy run, 2026-11-15):** Reconstructed the three Python files from GitHub connector source contents and ran `python3 -m unittest discover -v` in a separate container. Result: `Ran 12 tests ... OK`, exit code 0, no errors or failures. This was not a direct Git clone/check-out because internet name resolution from the execution container failed; original GitHub source was fetched through the connector. There has been no independent local-machine test.
- Seven distinct test methods exist; five run twice under discovery because `test_rigol_decimation.py` imports `Tests` from `test_rigol_capture.py`. Fix the import to avoid duplicate discovery if desired.
- Mock tests cover transfer chunking, waveform conversion/CSV metadata, RAW stopped-state protection, NORMAL mode, preamble mismatches and stride decimation. A pass does not verify actual instrument interoperability.

## Hardware-validated
- **None confirmed for this committed revision.**
- Earlier independent DS1054Z link-local routing and CH3 DC drift observations do not establish successful application waveform export.

## Hardware validation in progress — 2026-11-15
- **Ethernet reachability PASS:** PC `169.254.179.80` on `enp3s0f1` pinged scope `169.254.179.79`: 3/3 packets, 0% loss, mean RTT 0.262 ms.
- **NORMAL export NOT VALIDATED:** `python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 --mode normal --output test1_normal.csv` completed without exception, but produced only **1 sample** with reported x increment 0.01 s. Expected approximately 1200 display points with the proposed 500 us/div setup. Actual channel-display state, acquisition timebase and waveform preamble have not been confirmed. No voltage or timing check is possible from a single sample.
- **Investigation next:** verify CH2 enabled, visible waveform and STOP after SINGLE; query `*IDN?`, `:TRIG:STAT?`, `:CHAN2:DISP?`, `:ACQ:MDEP?`, `:TIM:SCAL?`, `:WAV:SOUR?`, `:WAV:MODE?`, `:WAV:FORM?`, `:WAV:PRE?` on the existing SCPI socket. Do not conclude a code defect without the instrument responses. Avoid committing test CSV until reviewed.

## Latest development — NORMAL transfer correction (2026-11-15)
- **Hardware diagnosis:** Both CH2 and CH4 displayed an arbitrary waveform with acquisition STOP. Original NORMAL CLI returned 1 sample per channel. Direct SCPI diagnostic on CH2 found residual `:WAV:STAR? = 5750001` and `:WAV:STOP? = 6000000`. Explicitly setting 1..1200 returned 1200 samples for CH2 and CH4. Scope preamble: `0,0,1200,1,1.000000e-02,-9.800000e-01,0,8.000000e-02,-75,127`.
- **Implemented:** `rigol_ds1054z_capture.py` now sets `:WAV:STAR` and `:WAV:STOP` explicitly for NORMAL as well as RAW, and raises on short NORMAL blocks rather than silently accepting a one-sample capture. Source commit `58ed029`.
- **Regression tests implemented, not yet executed:** `test_rigol_capture.py` adds stale-range reset and short-block rejection tests. Test commit `27c4121`. Re-run `python3 -m unittest discover -v` against this latest revision.
- **Verified on real instrument (direct diagnostic only):** 1200-byte NORMAL blocks on CH2 and CH4 after setting range. The revised CLI, CSV contents, analog scaling and timing are **not yet** instrument-validated.
- **Next hardware step:** `git pull --ff-only` locally, then repeat NORMAL CLI export with `--channels 2 4 --mode normal`. Expect 1200 samples per channel; review counts, CSV timebase and voltage against the scope display. Do not treat earlier direct diagnostic as full application validation.
- Local checkout will be behind GitHub until pulled; application source and test modifications have been committed to main. The SHA of the commit adding this SESSION_STATE update will be HEAD; check `git rev-parse HEAD` after pull.

## Hardware retest — NORMAL CLI successful (2026-11-15)
- User confirmed CH2 and CH4 both displayed the supplied arbitrary waveform with acquisition STOP.
- After the NORMAL range fix, command: `python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 4 --mode normal --output test1_normal_fixed.csv`.
- **Hardware-validated transfer count:** CH2 `1200/1200` and CH4 `1200/1200`, both 100%, decimate 1, no CLI errors; reported original/saved interval `0.01 s` per channel. Expected 2400 waveform rows plus CSV header, but file itself has **not** been inspected.
- **Not yet validated:** CSV values and row/index/time ordering, voltage and timing accuracy against display, RAW transfers, scope memory handling, and multi-chunk hardware transfers.
- **Next:** request the CSV (or analyze locally) plus scope timebase/Vpp; then test modest RAW memory depth with acquisition stopped. Do not label full application hardware-validated solely from the successful NORMAL count.
- GitHub documentation commit follows this test; local copy should use `git pull --ff-only` before further work.

## Latest test evidence — RAW acquisition and NORMAL CSV review (2026-11-15)
- On stopped DS1054Z with active CH2/CH4, user ran: `python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 4 --mode raw --output test2_raw.csv`.
- **Hardware-validated RAW transfer (CLI log):** CH2 and CH4 each completed 6,000,000/6,000,000 samples, in 24 blocks of 250,000 per channel, reporting original sample spacing 2e-06 s and 100% completion. The output was reported >1 GB; full RAW CSV was not uploaded/inspected.
- **NORMAL CSV inspected:** user-provided `test1_normal_fixed.csv` contains exactly 2400 waveform rows (1200/channel), with indices 0..1199 contiguous on each and scope-relative time -0.98..11.01 s at 0.01 s increments. CH2 exported voltage range -0.08..8.08 V, CH4 1.76..8.00 V. These are CSV-derived values, **not** externally validated analogue amplitudes. Oscilloscope identity reported DS1054Z firmware 00.04.04.SP4.
- **Existing optional reduction:** `--decimate N` is already present and source-implemented. N=500 would reduce a 6M-point channel to 12000 output rows and set saved spacing to 1 ms, but instrument transfer still reads all 6M points. No real-instrument decimated capture has yet been evidenced.
- **Planned:** Consider additional `--downsample` strategies such as min/max envelope per block to retain narrow peaks; not implemented. Do not misrepresent stride decimation as anti-aliased resampling.
- **Outstanding:** verify voltage/time against scope measurements, CSV sample integrity for RAW, real hardware `--decimate` behaviour, execute the new offline regression tests, and consider keeping large capture CSVs outside Git.
- The docs update is newer than the user's local checkout; synchronize with `git pull --ff-only` before developing.

## Latest hardware test — RAW decimation (2026-11-15)
- After `git pull --ff-only` reported already up to date, user ran `python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 4 --mode raw --decimate 500 --output test2_raw_decimated.csv` on the stopped Rigol.
- **Hardware-validated transfer and reduction counts:** CH2 and CH4 each completed 6,000,000/6,000,000 retrieved samples in 24 blocks of 250,000, writing 12,000 rows/channel at 1 ms reported output spacing (original 2 us); no console errors. Expected CSV data rows: 24,000. No independent CSV file inspection or voltage/time accuracy check yet.
- **Planned next revision:** desktop GUI exposing host/interface, channel boxes, RAW/NORMAL mode, decimation, CSV output, progress and errors, while preserving the existing command-line engine and stopped-acquisition safeguard. No GUI committed yet.
- **Next action:** obtain `test2_raw_decimated.csv` to inspect index/time/voltage progression; develop GUI on a new revision with offline tests before instrument testing. Latest commit for this document is the current branch HEAD after this update; obtain SHA from GitHub or local `git rev-parse HEAD`.
- Local checkout will need another `git pull --ff-only` after documentation-only commits.

## Attached RAW CSV validation and GUI dependency choice — 2026-11-15
- Uploaded `test2_raw_decimated(1).csv` inspected: 2,808,516 bytes; 24,000 data rows, 12,000/channel. CH2 and CH4 each have original sample indices 0..5,999,500 (stride 500), no gaps/duplicates; times -0.98..11.019 s at exactly 0.001 s increments. CH2 min/max 0..8.03578125 V, CH4 1.84570323..7.99804733 V. Uniform scope identity/UTC export timestamp. **Hardware-exported file structural validation PASS; absolute analogue accuracy still unverified.**
- Inspected CPX400DP source on `FLRHW/PSU_control` `dev`, particularly `scripts/cpx400dp_gui.py`: tries PySide6 then PyQt5, uses QProcess/QThread, QSettings and common Qt widgets. Decision for planned Rigol GUI: use the same Qt binding fallback and same Python environment, keeping the current standard-library CLI unchanged. **GUI not implemented.**
- Next: build Qt frontend with channel selection, host/interface, mode/decimation, output path, progress/error reporting, settings retention and responsive capture. Add offline tests; run GUI on real workstation.
- After this documentation update, local `main` will need `git pull --ff-only`.

## Qt GUI development session — 2026-11-15

- Source reviewed on GitHub before coding; main capture engine `rigol_ds1054z_capture.py` left unchanged.
- **Implemented in committed source:** `rigol_ds1054z_gui.py` using CPX400DP-compatible PySide6/PyQt5 fallback. Input controls for host, optional interface, port, timeout, CH1–CH4, RAW/NORMAL mode, decimation, chunk points and CSV path. QProcess invokes the CLI, displays merged live output, per-channel aggregate progress, Cancel, error/completion status, overwrite confirmation, and QSettings persistence. No GUI-owned SCPI connection and no automatic acquisition START/STOP.
- **Implemented in committed source:** `rigol_gui_core.py` pure-Python validated CLI argument builder and `test_rigol_gui_core.py` unit tests; `README.md`; `.gitignore` for generated captures and Python caches.
- **Existing test fixes:** Updated `test_rigol_capture.py` NORMAL-mode expectation to require explicit STAR/STOP commands, matching the hardware-fixed application code; removed duplicate unittest discovery by no longer importing the `Tests` test class into `test_rigol_decimation.py`.
- **CI setup:** `.github/workflows/offline-tests.yml` runs compileall plus unittest discovery under Python 3.12 on pushes and PRs. The latest combined commit status lookup contained no reported statuses; **do not claim a passing CI run** until the Actions run and logs are verified.
- **Offline-tested for this revision:** Not yet independently executed; new Qt GUI and tests require actual test run. Prior successful offline source-copy tests apply to an earlier revision only.
- **Hardware-validated for this revision:** Qt GUI not yet launched or used against an instrument. Earlier CLI tests (NORMAL 1200/channel; RAW 6M/channel; decimate 500 12000/channel; uploaded CSV index/time integrity) remain historical verified findings, but do not validate GUI behaviour.
- **Known potential issues:** Qt binding availability depends on using the same Python interpreter as CPX400DP. Cancellation may leave a partial CSV. Progress is based on lines written to CLI output, not byte-level wire progress. Existing CSV overwrites are confirmed before capture; GUI has no waveform preview.
- **Next:** `git pull --ff-only` on Kubuntu; run `python3 -m unittest discover -v`; launch `python3 rigol_ds1054z_gui.py` and check controls/layout, remembered values, no new dependencies, and a CH2+CH4 stopped acquisition RAW decimate-500 capture. Record terminal/GUI observations and update docs. Optionally inspect GitHub Actions status in repository.
- GitHub HEAD after this document update is the current documentation commit (inspect `git rev-parse HEAD` locally after pull). Do not mistake earlier pinned commit SHAs in historic sections for HEAD.

## 2026-11-16 — Simplified connection GUI / automatic interface selection
- **User hardware report before this change:** previous Qt GUI capture worked on physical DS1054Z (user reported; no UI logs attached). User requested automatic network interface selection and default port without needing to understand Linux adapter names.
- **Source implemented:** `rigol_network.py` automatically probes a user-entered scope host using system routing first, then route-device and other active IPv4 adapters (Linux `ip` output), verifying `*IDN?` includes `RIGOL` on a short-lived socket before invoking the existing capture CLI. No new third-party modules; uses only Python standard library and the already installed Qt bindings.
- **Source implemented:** `rigol_ds1054z_gui.py` runs the check in a QThread, preventing interface discovery from freezing the GUI, displays chosen network path in the console, and places optional manual interface, TCP port (default 5555), timeout and transfer chunk controls inside initially collapsed Advanced Settings. Auto connection is the default even for saved configurations containing the old fixed interface. Manual override and changed port are reflected in the status hint. The capture backend and its RAW STOP check were not changed.
- **Offline tests implemented:** `test_rigol_network.py` mocks Linux route and address enumeration plus identity-probe fallback; CI compile step now includes the new module. **Tests not yet independently executed in this session; CI pass not independently established.**
- **Hardware status:** automated interface probing and new GUI settings have not yet been tried on Kubuntu + DS1054Z. Prior successful manual-interface GUI capture is historical user-reported evidence only, not proof that auto mode works.
- **Next steps:** Pull main; run `python3 -m unittest discover -v`; launch `python3 rigol_ds1054z_gui.py`, leave Advanced Settings collapsed, use known host `169.254.179.79`, CH2+CH4 RAW with `--decimate 500` equivalent. Expect console `Network path: automatic system route` or chosen interface `enp3s0f1`, a successful capture, and no need to enter TCP port or adapter name. If auto fails, expand Advanced and set `enp3s0f1` manually for comparison.
- **Limits:** this is host-to-interface detection, **not host/IP discovery**. Host address still required; port 5555 is a default with override, not a dynamically discovered service. Scope connectivity requires valid host interface addressing and routing.
- Obtain the latest HEAD from `git rev-parse HEAD` after pull; prior commit references in older sections are historical.

## Known problems / limitations
- Earlier isolated source-copy test suite passed before the NORMAL fix; updated regression tests require execution. NORMAL CSV structure and two-channel RAW transfer counts are now confirmed; RAW CSV contents and analog/time accuracy still need validation.
- NORMAL full-size transfer is now confirmed on hardware; short-block *rejection* remains a regression-test/software path not physically exercised.
- Export may leave a partial CSV if a transfer fails.
- CSV UTC timestamp is PC export time, not acquisition timestamp or PSU-aligned timestamp.
- Decimation reduces CSV rows only, not Ethernet transfer time; stride decimation can miss narrow pulses.
- Unresolved instrument CH3 25 V DC drift from earlier hardware investigation; keep separate from application bugs.
- User's local Git checkout will be behind remote after documentation updates.

## Next steps
1. On local machine: `cd /mnt/Data/01_Engineering/01_Projects/301_Rigol_DS1054Z/Rigol_capture && git pull --ff-only && git status && git log -3 --oneline`.
2. Optionally reproduce the offline suite locally with `python3 -m unittest discover -v`; avoid committing generated `__pycache__` files. Fix the duplicate-discovery import when next modifying tests.
3. Check connectivity to the DS1054Z (known example: host `169.254.179.79`, interface `enp3s0f1`); stop acquisition via front panel / SINGLE completion.
4. Run controlled single-channel RAW and NORMAL exports, comparing known safe signals against on-screen voltage/time measurements. Record sample count, scale, scope configuration, firmware, command, errors and output.
5. Repeat on two channels; investigate transfer size, partial CSV behavior and any preamble mismatch if seen.
6. Update documentation with exact evidence and revisions, commit changes and confirm code/document consistency.

## Documentation rule
After significant changes, especially hardware tests, update `PROJECT_HANDOVER.md` (durable engineering history) and this file (current actual status). Label source-implemented, tests-executed, instrument-validated, and planned work explicitly. Documentation should be checked against committed code before a session ends.
