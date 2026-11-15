Rigol DS1054Z independent development capture utility, version 2.
Requires Python 3 standard library only. Not part of the CPX400DP application.

Scope: acquire waveform with SINGLE mode; once it has stopped, run:
  python3 rigol_ds1054z_capture.py --host 169.254.179.79 --interface enp3s0f1 --channels 2 4 --mode raw --output rigol_raw.csv

For the legacy 1,200-point screen display export:
  python3 rigol_ds1054z_capture.py --host 169.254.179.79 --channels 2 4 --mode normal --output rigol_screen.csv

RAW (default) uses Rigol :WAV:MODE RAW, :WAV:PRE?, :WAV:STAR, :WAV:STOP,
:WAV:DATA?; reads 1-based contiguous blocks of up to 250,000 samples each.
Works only on a stopped scope: utility checks :TRIG:STAT? and refuses to run
if the scope is still acquiring. It never issues :STOP or :RUN.

All displayed/enabled scope channels share acquisition memory, so reducing
active channels may allow longer/higher-resolution captures. Choose memory
and timebase on the scope itself before acquisition; this utility only exports.

The CSV contains actual instrument preamble X increment and voltage scaling.
Timestamps are scope-relative, NOT aligned to PSU runner elapsed times.
RAW CSVs can be very large; at 1 million points/channel expect tens of MB.
If acquisition memory is huge, consider lowering memory depth on the scope.
Do not unplug the scope or use DSRremote while transferring the record.
