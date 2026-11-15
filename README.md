# Rigol DS1054Z waveform capture

Standalone Python capture utility for stopped Rigol DS1054Z acquisitions over Ethernet. It includes a command-line exporter and a small Qt desktop frontend.

## Launch the GUI

The GUI reuses the Qt bindings used by the [CPX400DP PSU controller](https://github.com/FLRHW/PSU_control): **PySide6**, falling back to **PyQt5**. Use the same Python interpreter/environment that runs the CPX400DP GUI. The underlying capture engine uses only the Python standard library.

```bash
python3 rigol_ds1054z_gui.py
```

Select host and optional Linux interface, channels CH1–CH4, RAW or NORMAL mode, decimation factor, transfer chunk size and CSV output location. Choose **Capture waveform**. The progress bar tracks channel transfer completion. Connection errors and status appear in the console pane. **Cancel transfer** terminates the subprocess; a partially written CSV may remain.

The GUI remembers settings between launches using Qt's QSettings.

The GUI never changes oscilloscope RUN/STOP state. Prepare acquisition on the oscilloscope and STOP it (or wait for SINGLE to complete) before RAW export. It never issues commands directly to the instrument; it launches the existing CLI engine as a subprocess.

## CLI (no GUI dependency)

```bash
python3 rigol_ds1054z_capture.py \
  --host 169.254.179.79 --interface enp3s0f1 \
  --channels 2 4 --mode raw --decimate 500 \
  --output captures/rigol_reduced.csv
```

`--decimate 500` saves every 500th acquired sample, preserving original indices and scope-relative timestamps. **All samples are still transferred from the oscilloscope**; transfer duration is not reduced. Simple stride selection can miss narrow transients. Full resolution uses `--decimate 1`.

Default SCPI port is 5555. Two active channels can affect available acquisition memory on the scope. The exporter streams CSV rows as it receives waveform samples. See `README.txt` and `README_v2_1.txt` for legacy usage.

## Offline tests

```bash
python3 -m unittest discover -v
```

The GUI argument builder has tests requiring no Qt installation or hardware; the capture engine tests use simulated SCPI replies. GitHub Actions also runs offline tests. A successful offline test does not establish instrument voltage accuracy.

## Project continuity

Read `docs/PROJECT_HANDOVER.md` for architecture and decisions and `docs/SESSION_STATE.md` for active development, validation status and next steps. Do not commit large CSV captures. The `captures/` directory is gitignored.

## Hardware safety and scope

Do not rely on the tool as a safety interlock. Confirm safe input voltage, probe ratio and grounding. Acquisition occurs on the scope; the tool is an exporter, not an oscilloscope acquisition controller or a synchronized CPX400DP recorder.
