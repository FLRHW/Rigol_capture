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
- **Tests implemented but not executed during this session.** Test scripts use mocked SCPI socket.
- Command to run: `python3 -m unittest discover -q`.
- Until execution results are reported, do not mark this revision as passing.

## Hardware-validated
- **None confirmed for this committed revision.**
- Earlier independent DS1054Z link-local routing and CH3 DC drift observations do not establish successful application waveform export.

## Known problems / limitations
- Need actual test execution and instrument validation of RAW/NORMAL modes, data length, analog scale, timing and multi-channel behavior.
- NORMAL-mode shorter-than-preamble first block handling is unverified on hardware.
- Export may leave a partial CSV if a transfer fails.
- CSV UTC timestamp is PC export time, not acquisition timestamp or PSU-aligned timestamp.
- Decimation reduces CSV rows only, not Ethernet transfer time; stride decimation can miss narrow pulses.
- Unresolved instrument CH3 25 V DC drift from earlier hardware investigation; keep separate from application bugs.
- User's local Git checkout will be behind remote after documentation updates.

## Next steps
1. On local machine: `cd /mnt/Data/01_Engineering/01_Projects/301_Rigol_DS1054Z/Rigol_capture && git pull --ff-only && git status && git log -3 --oneline`.
2. Run `python3 -m unittest discover -q` locally and report full results; avoid committing generated `__pycache__` files.
3. Check connectivity to the DS1054Z (known example: host `169.254.179.79`, interface `enp3s0f1`); stop acquisition via front panel / SINGLE completion.
4. Run controlled single-channel RAW and NORMAL exports, comparing known safe signals against on-screen voltage/time measurements. Record sample count, scale, scope configuration, firmware, command, errors and output.
5. Repeat on two channels; investigate transfer size, partial CSV behavior and any preamble mismatch if seen.
6. Update documentation with exact evidence and revisions, commit changes and confirm code/document consistency.

## Documentation rule
After significant changes, especially hardware tests, update `PROJECT_HANDOVER.md` (durable engineering history) and this file (current actual status). Label source-implemented, tests-executed, instrument-validated, and planned work explicitly. Documentation should be checked against committed code before a session ends.
