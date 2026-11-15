"""Offline tests for the GUI argument builder; no Qt installation required."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from rigol_gui_core import capture_arguments


class GuiArgumentsTests(unittest.TestCase):
    def test_default_dual_channel_raw(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "capture.csv"
            args = capture_arguments(
                " 169.254.179.79 ", " enp3s0f1 ", [4, 2], "raw", 500, output
            )
            self.assertEqual(args[args.index("--host") + 1], "169.254.179.79")
            self.assertEqual(args[args.index("--mode") + 1], "raw")
            self.assertEqual(args[args.index("--decimate") + 1], "500")
            self.assertEqual(args[args.index("--channels") + 1:args.index("--mode")], ["2", "4"])
            self.assertEqual(args[args.index("--output") + 1], str(output))
            self.assertEqual(args[-2:], ["--interface", "enp3s0f1"])

    def test_optional_interface(self):
        args = capture_arguments("scope.local", "", [1], "normal", 1, "capture.csv")
        self.assertNotIn("--interface", args)
        self.assertIn("normal", args)

    def test_missing_channel(self):
        with self.assertRaisesRegex(ValueError, "channel"):
            capture_arguments("scope", "eth0", [], "raw", 1, "x.csv")

    def test_missing_host(self):
        with self.assertRaisesRegex(ValueError, "host"):
            capture_arguments(" ", "", [2], "raw", 1, "x.csv")

    def test_bad_decimation(self):
        with self.assertRaisesRegex(ValueError, "decimation"):
            capture_arguments("scope", "", [2], "raw", 0, "x.csv")

    def test_bad_chunk(self):
        with self.assertRaisesRegex(ValueError, "chunk"):
            capture_arguments("scope", "", [2], "raw", 1, "x.csv", chunk_points=250001)

    def test_bad_port(self):
        with self.assertRaisesRegex(ValueError, "port"):
            capture_arguments("scope", "", [2], "raw", 1, "x.csv", port=0)


if __name__ == "__main__":
    unittest.main()
