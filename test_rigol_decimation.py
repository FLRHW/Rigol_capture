"""Decimation stays aligned to acquisition index across RAW transfer blocks."""
import csv
import io
import unittest
from unittest.mock import patch
from rigol_ds1054z_capture import Rigol
from test_rigol_capture import FakeSocket


class DecimationTests(unittest.TestCase):
    def session(self, fake):
        with patch('rigol_ds1054z_capture.socket.create_connection', return_value=fake):
            return Rigol('169.254.179.79')

    def test_chunk_boundary_and_preserved_times(self):
        fake = FakeSocket(count=17)
        session = self.session(fake)
        text = io.StringIO()
        exported, dx = session.export_channel(csv.writer(text), 2, 'raw', 'time', 'RIGOL',
                                              chunk_points=3, decimate=5)
        rows = list(csv.reader(io.StringIO(text.getvalue())))
        self.assertEqual(exported, 4)
        self.assertEqual([int(row[3]) for row in rows], [0, 5, 10, 15])
        self.assertEqual([float(row[4]) for row in rows], [-.1, -.05, 0., .05])
        self.assertEqual([float(row[5]) for row in rows], [0., .25, .5, .75])
        self.assertEqual(dx, 0.01)

    def test_bad_decimation(self):
        fake = FakeSocket(count=3)
        session = self.session(fake)
        with self.assertRaisesRegex(ValueError, 'Decimation'):
            session.export_channel(csv.writer(io.StringIO()),2,'raw','time','RIGOL', decimate=0)


if __name__ == '__main__':
    unittest.main()
