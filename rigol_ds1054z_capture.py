#!/usr/bin/env python3
"""Standalone Rigol DS1000Z stopped-waveform CSV exporter (standard library only).

RAW mode reads acquisition memory in contiguous <=250,000 BYTE-point chunks.
The scope must already be STOPped; this tool never starts/stops acquisition.
Normal mode retains the legacy 1,200-point display export.
"""
import argparse
import csv
from datetime import datetime, timezone
import socket
from pathlib import Path

MAX_BYTES_PER_CHUNK = 250_000
MAX_TOTAL_POINTS = 24_000_000  # DS1054Z maximum nominal depth; guard against malformed PRE?


class Rigol:
    def __init__(self, host, port=5555, timeout=15, interface=None):
        if interface:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.settimeout(timeout)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE,
                                     interface.encode('ascii') + b'\0')
                self.sock.connect((host, port))
            except Exception:
                self.sock.close()
                raise
        else:
            self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.pending = bytearray()

    def close(self):
        self.sock.close()

    def command(self, command):
        self.sock.sendall((command + '\n').encode('ascii'))

    def get(self, n):
        while len(self.pending) < n:
            chunk = self.sock.recv(max(32768, min(262144, n-len(self.pending))))
            if not chunk:
                raise ConnectionError('Rigol closed the SCPI TCP connection')
            self.pending.extend(chunk)
        result = bytes(self.pending[:n])
        del self.pending[:n]
        return result

    def readline(self):
        result = bytearray()
        while True:
            char = self.get(1)
            if char in (b'\r', b'\n'):
                if result:
                    return result.decode('ascii', 'replace').strip()
                continue
            result.extend(char)
            if len(result) > 4096:
                raise ValueError('SCPI text response unusually long')

    def query(self, command):
        self.command(command)
        return self.readline()

    def block(self, command):
        self.command(command)
        # Rigol sometimes leaves a newline after the preceding binary block.
        header = self.get(1)
        while header in (b'\r', b'\n'):
            header = self.get(1)
        if header != b'#':
            raise ValueError('Expected IEEE488.2 binary block header, got '+repr(header))
        widthchar = self.get(1)
        if not b'1' <= widthchar <= b'9':
            raise ValueError('Unexpected binary length-digit count')
        length = int(self.get(int(widthchar)))
        if length > MAX_BYTES_PER_CHUNK:
            raise ValueError('Rigol returned an oversized BYTE block')
        result = self.get(length)
        # May be delayed until next reply; block()/readline() skip delimiters.
        while self.pending[:1] in (b'\r', b'\n'):
            del self.pending[:1]
        return result

    @staticmethod
    def parse_preamble(text, mode):
        fields = [float(field.strip()) for field in text.replace(';', ',').split(',')]
        if len(fields) != 10:
            raise ValueError('Expected ten :WAV:PRE? fields: '+text)
        fmt, wave_mode, points, count, dx, x0, xref, dy, y0, yref = fields
        expected_mode = {'normal': 0, 'raw': 2}[mode]
        if int(fmt) != 0 or int(wave_mode) != expected_mode:
            raise ValueError(f'Unexpected waveform preamble format/mode ({fmt:g},{wave_mode:g}); '
                             f'expected BYTE/{mode.upper()}')
        if not (0 < points <= MAX_TOTAL_POINTS and points == int(points)):
            raise ValueError('Waveform point count out of range: '+str(points))
        if dx <= 0:
            raise ValueError('Invalid X increment: '+str(dx))
        return (int(points), dx, x0, xref, dy, y0, yref)

    def prepare_channel(self, channel, mode):
        self.command(f':WAV:SOUR CHAN{channel}')
        self.command(':WAV:MODE '+('RAW' if mode == 'raw' else 'NORM'))
        self.command(':WAV:FORM BYTE')
        preamble_text = self.query(':WAV:PRE?')
        return self.parse_preamble(preamble_text, mode)

    def export_channel(self, writer, channel, mode, timestamp, identity, chunk_points=MAX_BYTES_PER_CHUNK, decimate=1):
        points, dx, x0, xref, dy, y0, yref = self.prepare_channel(channel, mode)
        if chunk_points < 1 or chunk_points > MAX_BYTES_PER_CHUNK:
            raise ValueError('Chunk points must be between 1 and 250000')
        if decimate < 1:
            raise ValueError('Decimation factor must be >= 1')
        exported = 0
        written = 0
        while written < points:
            size = min(chunk_points, points-written)
            if mode == 'raw':
                # Rigol start/stop are inclusive and 1-based.
                self.command(f':WAV:STAR {written + 1}')
                self.command(f':WAV:STOP {written + size}')
            raw = self.block(':WAV:DATA?')
            if len(raw) != size:
                # NORM display may return fewer points than preamble; never
                # silently invent/duplicate points or misalign further blocks.
                if mode == 'normal' and written == 0 and len(raw) > 0:
                    points = len(raw)
                else:
                    raise ValueError(f'CH{channel}: requested {size} points at {written + 1}, got {len(raw)}')
            # Apply a global sample-index stride across RAW chunk boundaries.
            # Original timestamps and sample indices are preserved.
            for i, byte in enumerate(raw):
                index = written + i
                if index % decimate:
                    continue
                writer.writerow((timestamp, identity, channel, index,
                                 f'{(x0 + (index-xref)*dx):.12g}',
                                 f'{((byte-y0-yref)*dy):.9g}'))
                exported += 1
            written += len(raw)
            print(f'CH{channel}: {written}/{points} points ({100*written/points:.1f}%)', flush=True)
        print(f'CH{channel}: wrote {exported} of {written} acquired samples (decimate {decimate})')
        return exported, dx


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=5555)
    parser.add_argument('--interface', default=None, help='Linux Ethernet interface for link-local scopes')
    parser.add_argument('--channels', type=int, nargs='+', default=[2, 4])
    parser.add_argument('--mode', choices=('raw', 'normal'), default='raw')
    parser.add_argument('--output', type=Path, default=Path('rigol_scope.csv'))
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--chunk-points', type=int, default=MAX_BYTES_PER_CHUNK)
    parser.add_argument('--decimate', type=int, default=1,
                        help='Store only every Nth original sample (default 1 = no reduction)')
    args = parser.parse_args(argv)
    if not args.channels or any(ch not in (1, 2, 3, 4) for ch in args.channels):
        parser.error('Channels must be between 1 and 4')
    if args.chunk_points < 1 or args.chunk_points > MAX_BYTES_PER_CHUNK:
        parser.error('--chunk-points must be 1..250000')
    if args.decimate < 1:
        parser.error('--decimate must be an integer >= 1')
    session = Rigol(args.host, args.port, args.timeout, args.interface)
    try:
        identity = session.query('*IDN?')
        if 'RIGOL' not in identity.upper():
            raise ValueError('Unexpected SCPI instrument: '+identity)
        if args.mode == 'raw':
            # Read-only check: do not change scope acquisition or destroy data.
            state = session.query(':TRIG:STAT?').strip().upper()
            if state not in ('STOP', 'STOPPED'):
                raise RuntimeError(f'Rigol trigger state is {state!r}; STOP or Single-complete acquisition '
                                   'on the front panel before reading RAW data')
        timestamp = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Streaming output keeps memory bounded even for millions of samples.
        with args.output.open('w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['capture_utc', 'scope_idn', 'scope_channel', 'sample_index',
                             'scope_time_s', 'voltage_v'])
            for channel in args.channels:
                count, dt = session.export_channel(writer, channel, args.mode,
                                                   timestamp, identity, args.chunk_points, args.decimate)
                print(f'CH{channel}: exported {count} rows, saved spacing {dt*args.decimate:.12g} s '
                      f'(original spacing {dt:.12g} s)')
    finally:
        session.close()
    print('Saved:', args.output.resolve())
    print('Scope-relative timestamps only; no shared PC/PSU trigger timestamp.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
