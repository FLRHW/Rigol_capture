Rigol DS1054Z stopped-waveform exporter v2.1
=============================================

New option: --decimate N  (positive integer; default 1)

Example: keep one sample out of every 500, preserving original index/time:

  python3 rigol_ds1054z_capture.py \
    --host 169.254.179.79 --interface enp3s0f1 \
    --channels 2 4 --mode raw --decimate 500 \
    --output rigol_reduced.csv

For a single channel: --channels 2
Full-resolution RAW remains the default with --decimate 1.

Important: The utility still downloads every acquired point from the
oscilloscope, then stores only every Nth sample. It reduces exported CSV
size, not the scope-to-PC transfer time. At 4 us original sampling spacing,
--decimate 500 produces 2 ms saved spacing (and about 24,000 rows for two
channels across 24 s). The original sample_index and scope_time_s are kept.

Simple stride selection does not preserve very short pulses/glitches; use
--decimate 1 or a smaller factor for submillisecond analogue analysis.
Scope must be stopped before RAW export; this tool will not change RUN/STOP.

Uses Python standard library only. No connection to CPX400DP application.

Offline tests: python3 -m unittest discover -q
