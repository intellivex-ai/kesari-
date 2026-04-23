"""
Kesari AI — SSL Certificate Generator
Generates a self-signed certificate so the companion API can serve HTTPS
locally, enabling microphone/camera access without ngrok on LAN devices.
"""
import ipaddress
import logging
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

CERT_DIR = Path.home() / ".kesari_ai" / "ssl"
CERT_FILE = CERT_DIR / "kesari.crt"
KEY_FILE  = CERT_DIR / "kesari.key"


def _get_local_ips() -> list[str]:
    """Return all non-loopback IPv4 addresses of this machine."""
    ips = []
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    # Always include loopback
    if "127.0.0.1" not in ips:
        ips.append("127.0.0.1")
    return ips


def ensure_ssl_cert() -> tuple[Path, Path]:
    """
    Return (cert_path, key_path), generating a new self-signed cert if needed.
    The cert covers localhost + all detected LAN IPs so browsers on phones/iPads
    accept it without 'not secure' errors (after a one-time trust on the device).
    """
    CERT_DIR.mkdir(parents=True, exist_ok=True)

    if CERT_FILE.exists() and KEY_FILE.exists():
        # Re-use existing cert unless it's older than 1 year
        try:
            age = datetime.now(timezone.utc) - datetime.fromtimestamp(
                CERT_FILE.stat().st_mtime, tz=timezone.utc
            )
            if age.days < 360:
                return CERT_FILE, KEY_FILE
        except Exception:
            pass

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        raise RuntimeError(
            "cryptography package is required for HTTPS support. "
            "Run: pip install cryptography"
        )

    logger.info("Generating self-signed SSL certificate for Kesari HTTPS server…")

    # Generate key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # SAN: localhost + 127.0.0.1 + all LAN IPs
    san_dns = [x509.DNSName("localhost")]
    san_ips = [x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]

    for ip_str in _get_local_ips():
        if ip_str != "127.0.0.1":
            try:
                san_ips.append(x509.IPAddress(ipaddress.IPv4Address(ip_str)))
            except Exception:
                pass

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Kesari AI Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kesari AI"),
    ])

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(san_dns + san_ips),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    # Write key
    KEY_FILE.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    # Write cert
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"SSL cert written to {CERT_FILE}")
    return CERT_FILE, KEY_FILE
