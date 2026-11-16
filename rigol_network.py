"""Linux network-interface discovery for a known Rigol SCPI host.

Standard library only. Discovery confirms *IDN? before selecting a route.
It never broadcasts, changes host networking, or controls scope acquisition.
"""
import re
import socket
import subprocess

from rigol_ds1054z_capture import Rigol


def route_interface(host):
    """Return the interface in Linux's IPv4 routing decision, if available."""
    try:
        addresses = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
        ip = addresses[0][4][0]
        result = subprocess.run(
            ["ip", "-4", "route", "get", ip],
            capture_output=True, text=True, check=False, timeout=3,
        )
        if result.returncode == 0:
            match = re.search(r"(?:^|\s)dev\s+(\S+)", result.stdout)
            if match:
                return match.group(1)
    except (OSError, IndexError, socket.gaierror, subprocess.TimeoutExpired):
        pass
    return None


def ipv4_interfaces():
    """Active Linux interfaces with an IPv4 address; no external libraries."""
    try:
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", "up"],
            capture_output=True, text=True, check=False, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    names = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[2] == "inet":
            name = fields[1].split("@")[0]
            if name != "lo" and name not in names:
                names.append(name)
    return names


def candidate_interfaces(host):
    """Prefer default routing, then Linux's preferred device, then active NICs."""
    candidates = [None]  # unbound socket: let the kernel route first
    routed = route_interface(host)
    for name in [routed, *ipv4_interfaces()]:
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def probe_rigol(host, port=5555, interface=None, timeout=2.0):
    """Query identity via one connection, returning IDN if Rigol responds."""
    scope = Rigol(host, port=port, timeout=timeout, interface=interface)
    try:
        identity = scope.query("*IDN?").strip()
        if "RIGOL" not in identity.upper():
            raise ValueError("Unexpected instrument identity: " + identity)
        return identity
    finally:
        scope.close()


def find_interface(host, port=5555, override="", timeout=2.0):
    """Return (interface_or_None, IDN) for a verified Rigol connection.

    Explicit override is tried exclusively. In automatic mode, attempt Linux
    routing first, then bound active IPv4 interfaces. Probe is intended for a
    background worker, not the GUI event thread.
    """
    if override.strip():
        selected = override.strip()
        return selected, probe_rigol(host, port, selected, timeout)
    errors = []
    for interface in candidate_interfaces(host):
        try:
            return interface, probe_rigol(host, port, interface, timeout)
        except (OSError, ValueError, TimeoutError) as exc:
            errors.append(f"{interface or 'system route'}: {exc}")
    raise ConnectionError(
        "No verified Rigol SCPI connection at "
        f"{host}:{port}. Tried: " + "; ".join(errors)
    )
