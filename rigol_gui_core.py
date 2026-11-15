"""Qt-independent validation and CLI argument assembly for the Rigol GUI."""
from pathlib import Path


def capture_arguments(host, interface, channels, mode, decimate, output,
                      port=5555, timeout=20, chunk_points=250000):
    """Return validated argv for rigol_ds1054z_capture.py (no Qt dependency)."""
    host = str(host).strip()
    interface = str(interface).strip()
    if not host or any(ch.isspace() for ch in host):
        raise ValueError("Enter a valid host name or IP address (without spaces).")
    selected = sorted(set(channels))
    if not selected or any(ch not in (1, 2, 3, 4) for ch in selected):
        raise ValueError("Select at least one valid channel (CH1–CH4).")
    if mode not in ("raw", "normal") or decimate < 1:
        raise ValueError("Invalid acquisition mode or decimation factor.")
    if not (1 <= port <= 65535 and timeout > 0 and 1 <= chunk_points <= 250000):
        raise ValueError("Invalid port, timeout or chunk size.")
    if not str(output).strip():
        raise ValueError("Choose an output CSV file.")
    args = [
        "--host", host, "--port", str(port),
        "--channels", *(str(ch) for ch in selected),
        "--mode", mode, "--decimate", str(decimate),
        "--output", str(Path(output).expanduser().resolve()),
        "--timeout", str(timeout),
        "--chunk-points", str(chunk_points),
    ]
    if interface:
        args.extend(["--interface", interface])
    return args
