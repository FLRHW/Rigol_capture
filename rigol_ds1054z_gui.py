#!/usr/bin/env python3
"""Qt frontend for the independent Rigol DS1054Z CSV capture CLI.

The existing CLI is invoked as a child process and remains the only owner of
the instrument TCP connection. No instrument SCPI commands are sent by the GUI.
Requires PySide6 or PyQt5 (the same bindings used by CPX400DP).
"""
import re
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QProcess, QSettings, QTimer
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
        QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
        QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox,
        QDoubleSpinBox, QVBoxLayout, QWidget,
    )
    QT_LIBRARY = "PySide6"
except ImportError:
    try:
        from PyQt5.QtCore import QProcess, QSettings, QTimer
        from PyQt5.QtWidgets import (
            QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
            QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
            QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox,
            QDoubleSpinBox, QVBoxLayout, QWidget,
        )
        QT_LIBRARY = "PyQt5"
    except ImportError:
        raise SystemExit(
            "Neither PySide6 nor PyQt5 is available to this Python interpreter. "
            "Run the GUI with the same interpreter as CPX400DP."
        )

HERE = Path(__file__).resolve().parent
BACKEND = HERE / "rigol_ds1054z_capture.py"
PROGRESS_RE = re.compile(r"^CH([1-4]): (\d+)/(\d+) points \(([\d.]+)%\)$")


def capture_arguments(host, interface, channels, mode, decimate, output,
                      port=5555, timeout=20, chunk_points=250000):
    """Validate and build backend CLI args; independent of Qt for testing."""
    host = host.strip()
    interface = interface.strip()
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


class CaptureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rigol DS1054Z — Waveform Capture")
        self.resize(780, 660)
        self.settings = QSettings("FLRHW", "RigolCapture")
        self.process = None
        self.pending_lines = ""
        self.cancel_requested = False
        self.progress_by_channel = {}
        self.expected_channels = []
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)
        form = QFormLayout()
        self.host = QLineEdit()
        self.host.setPlaceholderText("169.254.179.79")
        form.addRow("Oscilloscope host", self.host)
        self.interface = QLineEdit()
        self.interface.setPlaceholderText("Optional, e.g. enp3s0f1")
        form.addRow("Network interface", self.interface)

        network = QHBoxLayout()
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(5555)
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0.1, 3600)
        self.timeout.setDecimals(1)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(20)
        network.addWidget(QLabel("Port"))
        network.addWidget(self.port)
        network.addSpacing(12)
        network.addWidget(QLabel("Socket timeout"))
        network.addWidget(self.timeout)
        network.addStretch()
        form.addRow("Connection", network)
        layout.addLayout(form)

        options = QGroupBox("Capture settings")
        opts = QGridLayout(options)
        self.channels = {}
        channel_row = QHBoxLayout()
        for ch in range(1, 5):
            control = QCheckBox(f"CH{ch}")
            self.channels[ch] = control
            channel_row.addWidget(control)
        channel_row.addStretch()
        opts.addWidget(QLabel("Channels"), 0, 0)
        opts.addLayout(channel_row, 0, 1, 1, 3)

        self.mode = QComboBox()
        self.mode.addItem("RAW — full acquisition memory", "raw")
        self.mode.addItem("NORMAL — display waveform", "normal")
        opts.addWidget(QLabel("Capture mode"), 1, 0)
        opts.addWidget(self.mode, 1, 1, 1, 3)

        self.decimate = QSpinBox()
        self.decimate.setRange(1, 100000000)
        self.decimate.setValue(500)
        self.decimate.setToolTip(
            "Save every Nth sample. All instrument samples are still downloaded; "
            "narrow glitches can be missed."
        )
        opts.addWidget(QLabel("Keep every Nth sample"), 2, 0)
        opts.addWidget(self.decimate, 2, 1)

        self.chunk = QSpinBox()
        self.chunk.setRange(1, 250000)
        self.chunk.setValue(250000)
        opts.addWidget(QLabel("Transfer chunk (points)"), 3, 0)
        opts.addWidget(self.chunk, 3, 1)
        layout.addWidget(options)

        output_row = QHBoxLayout()
        self.output = QLineEdit()
        self.browse = QPushButton("Browse…")
        self.browse.clicked.connect(self._browse)
        output_row.addWidget(self.output, 1)
        output_row.addWidget(self.browse)
        layout.addWidget(QLabel("Output CSV"))
        layout.addLayout(output_row)

        self.note = QLabel(
            "Prepare and STOP the oscilloscope acquisition before RAW export. "
            "This GUI does not issue RUN/STOP commands."
        )
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.status = QLabel("Ready")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Capture waveform")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton("Cancel transfer")
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)

        layout.addWidget(QLabel("Console output"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console, 1)

    def _load_settings(self):
        self.host.setText(str(self.settings.value("host", "169.254.179.79")))
        self.interface.setText(str(self.settings.value("interface", "enp3s0f1")))
        self.port.setValue(int(self.settings.value("port", 5555)))
        self.timeout.setValue(float(self.settings.value("timeout", 20)))
        self.chunk.setValue(int(self.settings.value("chunk", 250000)))
        self.decimate.setValue(int(self.settings.value("decimate", 500)))
        mode = str(self.settings.value("mode", "raw"))
        self.mode.setCurrentIndex(max(0, self.mode.findData(mode)))
        selected = str(self.settings.value("channels", "2,4")).split(",")
        for ch, cb in self.channels.items():
            cb.setChecked(str(ch) in selected)
        self.output.setText(str(self.settings.value(
            "output", str(HERE / "captures" / "rigol_scope.csv")
        )))

    def _save_settings(self):
        for key, value in (
            ("host", self.host.text().strip()),
            ("interface", self.interface.text().strip()),
            ("port", self.port.value()),
            ("timeout", self.timeout.value()),
            ("chunk", self.chunk.value()),
            ("decimate", self.decimate.value()),
            ("mode", self.mode.currentData()),
            ("channels", ",".join(str(ch) for ch in self.expected_channels)),
            ("output", self.output.text().strip()),
        ):
            self.settings.setValue(key, value)
        self.settings.sync()

    def _browse(self):
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save waveform CSV", self.output.text().strip(), "CSV files (*.csv)"
        )
        if chosen:
            self.output.setText(chosen)

    def _append(self, message):
        self.console.appendPlainText(message)

    def _set_running(self, running):
        for control in (
            self.host, self.interface, self.port, self.timeout, self.mode,
            self.decimate, self.chunk, self.output, self.browse,
            *self.channels.values(),
        ):
            control.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    def _start(self):
        if self.process is not None:
            return
        self.expected_channels = [ch for ch, cb in self.channels.items() if cb.isChecked()]
        try:
            args = capture_arguments(
                self.host.text(), self.interface.text(), self.expected_channels,
                self.mode.currentData(), self.decimate.value(), self.output.text(),
                self.port.value(), self.timeout.value(), self.chunk.value(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid capture settings", str(exc))
            return
        output_path = Path(self.output.text().strip()).expanduser().resolve()
        if output_path.exists():
            answer = QMessageBox.question(
                self, "Overwrite CSV?",
                f"{output_path}\n\nThis file already exists. Replace it?"
            )
            if answer != QMessageBox.Yes:
                return
        self._save_settings()
        self.console.clear()
        self.pending_lines = ""
        self.progress_by_channel = {}
        self.cancel_requested = False
        self.progress.setValue(0)
        self.status.setText("Connecting / waiting for instrument…")
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.setWorkingDirectory(str(HERE))
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._set_running(True)
        # -u forces progress lines out promptly, even when subprocess output is piped.
        self.process.start(sys.executable, ["-u", str(BACKEND), *args])

    def _read_output(self):
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        self.pending_lines += chunk
        while "\n" in self.pending_lines:
            line, self.pending_lines = self.pending_lines.split("\n", 1)
            self._handle_line(line.rstrip("\r"))

    def _handle_line(self, line):
        self._append(line)
        match = PROGRESS_RE.match(line)
        if match:
            channel, done, total, _ = match.groups()
            if int(total) > 0:
                self.progress_by_channel[int(channel)] = min(1.0, int(done) / int(total))
                overall = sum(self.progress_by_channel.get(ch, 0)
                              for ch in self.expected_channels)
                self.progress.setValue(round(100 * overall / len(self.expected_channels)))
                self.status.setText(f"Receiving CH{channel}: {done}/{total} points")

    def _cancel(self):
        if self.process is None:
            return
        self.cancel_requested = True
        self.cancel_button.setEnabled(False)
        self.status.setText("Cancelling… (output may be partial)")
        self.process.terminate()
        process = self.process
        QTimer.singleShot(
            3000,
            lambda: process.kill() if process.state() != QProcess.NotRunning else None,
        )

    def _process_error(self, error):
        if self.process is not None:
            self._append(f"Process error: {self.process.errorString()}")

    def _finished(self, exit_code, exit_status):
        self._read_output()
        if self.pending_lines:
            self._handle_line(self.pending_lines)
            self.pending_lines = ""
        if self.cancel_requested:
            self.status.setText("Cancelled. A partial CSV may remain.")
        elif exit_code == 0 and exit_status == QProcess.NormalExit:
            self.progress.setValue(100)
            self.status.setText("Capture complete — CSV saved")
        else:
            self.status.setText(
                f"Capture FAILED (exit code {exit_code}); a partial CSV may remain."
            )
        self._set_running(False)
        self.process.deleteLater()
        self.process = None

    def closeEvent(self, event):
        if self.process is not None:
            QMessageBox.warning(
                self, "Capture in progress",
                "Cancel the transfer before closing. Partial CSV files may remain."
            )
            event.ignore()
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CaptureWindow()
    window.show()
    return app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
