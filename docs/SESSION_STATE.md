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

## Known problems / limitations
- Earlier isolated source-copy test suite passed before the NORMAL fix; updated regression tests require execution. NORMAL CLI transfer count confirmed on CH2/CH4 hardware; RAW, CSV data values, analog scale and timing still need validation.
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
