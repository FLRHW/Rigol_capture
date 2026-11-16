"""Simulated Rigol RAW/NORM SCPI tests, no hardware access."""
import csv
import io
import unittest
from unittest.mock import patch
from rigol_ds1054z_capture import Rigol, main
from pathlib import Path
from tempfile import TemporaryDirectory


class FakeSocket:
    def __init__(self, count=7, mode='raw', status='STOP'):
        self.sent = []
        self.pending = bytearray()
        self.count = count
        self.mode = mode
        self.status = status
        self.start = 1
        self.stop = count
    def settimeout(self, value): pass
    def close(self): pass
    def sendall(self, data):
        cmd = data.decode().strip()
        self.sent.append(cmd)
        if cmd == '*IDN?': self.pending.extend(b'RIGOL TECHNOLOGIES,DS1054Z,123,00\n')
        elif cmd == ':TRIG:STAT?': self.pending.extend((self.status+'\n').encode())
        elif cmd.startswith(':WAV:STAR '): self.start = int(cmd.split()[-1])
        elif cmd.startswith(':WAV:STOP '): self.stop = int(cmd.split()[-1])
        elif cmd == ':WAV:PRE?':
            modeid = 2 if self.mode == 'raw' else 0
            self.pending.extend(f'0,{modeid},{self.count},1,0.01,-0.1,0,0.05,100,0\n'.encode())
        elif cmd == ':WAV:DATA?':
            data = bytes((100 + i) for i in range(self.start-1,self.stop))
            self.pending.extend(f'#{len(str(len(data)))}{len(data)}'.encode()+data+b'\n')
    def recv(self, n):
        if not self.pending: raise TimeoutError('No fake scope response')
        result = bytes(self.pending[:n]); del self.pending[:n]
        return result

class Tests(unittest.TestCase):
    def session(self, fake):
        with patch('rigol_ds1054z_capture.socket.create_connection', return_value=fake):
            return Rigol('169.254.179.79')
    def test_raw_chunks_contiguous(self):
        fake=FakeSocket(count=7)
        scope=self.session(fake)
        out=io.StringIO(); writer=csv.writer(out)
        count,dt=scope.export_channel(writer,2,'raw','stamp','RIGOL',chunk_points=3)
        rows=list(csv.reader(io.StringIO(out.getvalue())))
        self.assertEqual(count,7)
        self.assertEqual(len(rows),7)
        self.assertEqual([int(row[3]) for row in rows],list(range(7)))
        self.assertEqual([round(float(row[5]),6) for row in rows],[round(i*.05,6) for i in range(7)])
        self.assertEqual([cmd for cmd in fake.sent if cmd.startswith(':WAV:STAR')],
                         [':WAV:STAR 1',':WAV:STAR 4',':WAV:STAR 7'])
        self.assertEqual([cmd for cmd in fake.sent if cmd.startswith(':WAV:STOP')],
                         [':WAV:STOP 3',':WAV:STOP 6',':WAV:STOP 7'])
    def test_full_cli_and_metadata(self):
        fake=FakeSocket(count=7)
        with TemporaryDirectory() as d:
            output=Path(d)/'capture.csv'
            with patch('rigol_ds1054z_capture.socket.create_connection',return_value=fake):
                self.assertEqual(main(['--host','169.254.179.79','--channels','2',
                                       '--output',str(output),'--chunk-points','3']),0)
            with output.open(newline='') as handle:
                rows=list(csv.DictReader(handle))
            self.assertEqual(len(rows),7)
            self.assertAlmostEqual(float(rows[6]['scope_time_s']),-.04)
    def test_requires_stopped_scope(self):
        fake=FakeSocket(status='RUN')
        with patch('rigol_ds1054z_capture.socket.create_connection',return_value=fake):
            with self.assertRaisesRegex(RuntimeError,'STOP'):
                main(['--host','x'])
        self.assertFalse(any(':WAV:DATA?' in cmd for cmd in fake.sent))
    def test_normal_mode(self):
        fake=FakeSocket(count=3,mode='normal')
        scope=self.session(fake)
        out=io.StringIO(); count,dt=scope.export_channel(csv.writer(out),2,'normal','stamp','RIGOL')
        self.assertEqual(count,3)
        self.assertIn(':WAV:STAR 1',fake.sent)
        self.assertIn(':WAV:STOP 3',fake.sent)
        self.assertEqual(len(list(csv.reader(io.StringIO(out.getvalue())))),3)
    def test_normal_resets_stale_raw_range(self):
        fake = FakeSocket(count=7, mode='normal')
        # Simulate residual waveform transfer settings from a prior RAW capture.
        fake.start = 5_750_001
        fake.stop = 6_000_000
        scope = self.session(fake)
        out = io.StringIO()
        count, _ = scope.export_channel(csv.writer(out), 2, 'normal', 'stamp', 'RIGOL')
        self.assertEqual(count, 7)
        self.assertIn(':WAV:STAR 1', fake.sent)
        self.assertIn(':WAV:STOP 7', fake.sent)
        self.assertEqual(len(list(csv.reader(io.StringIO(out.getvalue())))), 7)

    def test_normal_rejects_short_block(self):
        class ShortReplySocket(FakeSocket):
            def sendall(self, data):
                if data.decode().strip() == ':WAV:DATA?':
                    self.sent.append(':WAV:DATA?')
                    self.pending.extend(b'#11' + bytes([100]) + b'\\n')
                else:
                    super().sendall(data)
        fake = ShortReplySocket(count=3, mode='normal')
        scope = self.session(fake)
        with self.assertRaisesRegex(ValueError, 'requested 3 BYTE samples'):
            scope.export_channel(csv.writer(io.StringIO()), 2, 'normal', 'stamp', 'RIGOL')

    def test_short_block_diagnostic_is_explicit_and_never_silent(self):
        class ShortBlock(FakeSocket):
            def sendall(self, data):
                if data.decode().strip() == ':WAV:DATA?':
                    self.sent.append(':WAV:DATA?')
                    payload = bytes([100] * 128)
                    self.pending.extend(b'#3128' + payload + b'\\n')
                else:
                    super().sendall(data)
        fake = ShortBlock(count=1200)
        scope = self.session(fake)
        out = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            scope.export_channel(csv.writer(out), 4, 'raw', 'stamp', 'RIGOL')
        msg = str(caught.exception)
        for value in ('CH4 RAW', '1200 BYTE', '1..1200',
                      '128 BYTE', 'entire SCPI binary reply',
                      'partial CSV'):
            self.assertIn(value, msg)
        self.assertEqual(out.getvalue(), '')

    def test_reject_unexpected_mode(self):
        fake=FakeSocket(count=3,mode='normal')
        scope=self.session(fake)
        with self.assertRaisesRegex(ValueError,'Unexpected waveform preamble'):
            scope.prepare_channel(2,'raw')

if __name__=='__main__': unittest.main()
