"""Offline discovery tests; no Qt, network, or instrument required."""
import subprocess
import unittest
from unittest.mock import patch

from rigol_network import candidate_interfaces, find_interface, ipv4_interfaces, route_interface


class DiscoveryTests(unittest.TestCase):
    @patch("rigol_network.subprocess.run")
    @patch("rigol_network.socket.getaddrinfo")
    def test_route_interface(self, address, run):
        address.return_value = [(None, None, None, None, ("169.254.179.79", 0))]
        run.return_value = subprocess.CompletedProcess(
            [], 0, stdout="169.254.179.79 dev enp3s0f1 src 169.254.179.80\n"
        )
        self.assertEqual(route_interface("169.254.179.79"), "enp3s0f1")

    @patch("rigol_network.subprocess.run")
    def test_active_interfaces(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout=(
            "2: enp3s0f1    inet 169.254.179.80/16 brd 169.254.255.255 scope link enp3s0f1\n"
            "3: wlan0    inet 192.168.1.9/24 brd 192.168.1.255 scope global wlan0\n"
            "1: lo    inet 127.0.0.1/8 scope host lo\n"
        ))
        self.assertEqual(ipv4_interfaces(), ["enp3s0f1", "wlan0"])

    @patch("rigol_network.ipv4_interfaces", return_value=["eth0", "wlan0"])
    @patch("rigol_network.route_interface", return_value="eth0")
    def test_candidate_order_and_dedup(self, route, interfaces):
        self.assertEqual(candidate_interfaces("scope"), [None, "eth0", "wlan0"])

    @patch("rigol_network.probe_rigol")
    @patch("rigol_network.candidate_interfaces", return_value=[None, "eth0", "eth1"])
    def test_fallback_after_unbound_failure(self, candidates, probe):
        probe.side_effect = [
            ConnectionError("unbound route failed"),
            "RIGOL TECHNOLOGIES,DS1054Z,123,00",
        ]
        self.assertEqual(
            find_interface("scope", timeout=1),
            ("eth0", "RIGOL TECHNOLOGIES,DS1054Z,123,00")
        )
        self.assertEqual(probe.call_count, 2)

    @patch("rigol_network.probe_rigol")
    @patch("rigol_network.candidate_interfaces")
    def test_manual_override_is_exclusive(self, candidates, probe):
        probe.return_value = "RIGOL,DS1054Z"
        self.assertEqual(
            find_interface("scope", override=" enp3s0f1 "),
            ("enp3s0f1", "RIGOL,DS1054Z")
        )
        candidates.assert_not_called()
        probe.assert_called_once_with("scope", 5555, "enp3s0f1", 2.0)

    @patch("rigol_network.probe_rigol", side_effect=ValueError("other instrument"))
    @patch("rigol_network.candidate_interfaces", return_value=[None, "eth0"])
    def test_all_candidates_fail(self, candidates, probe):
        with self.assertRaisesRegex(ConnectionError, "No verified Rigol"):
            find_interface("scope")


if __name__ == "__main__":
    unittest.main()
