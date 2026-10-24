"""Read-only runtime probes; writes only synthetic fixtures in disposable /tmp and /data."""

import ctypes
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.request


def tls_checks():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CEPIO disposable TLS fixture")])
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False)
            .sign(key, hashes.SHA256())
        )
        (root / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (root / "key.pem").write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(root / "cert.pem", root / "key.pem")
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(10)
        address = listener.getsockname()
        outcomes = []

        def serve():
            for _ in range(3):
                try:
                    connection, _ = listener.accept()
                    with connection:
                        with server_context.wrap_socket(connection, server_side=True) as channel:
                            channel.recv(1)
                            channel.sendall(b"ok")
                except ssl.SSLError:
                    pass  # The two intentional negative certificate checks.
            listener.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        for trusted, hostname, expected in [
            (True, "localhost", True),
            (False, "localhost", False),
            (True, "wrong.invalid", False),
        ]:
            context = ssl.create_default_context(cafile=str(root / "cert.pem") if trusted else None)
            try:
                with socket.create_connection(address, timeout=5) as connection:
                    with context.wrap_socket(connection, server_hostname=hostname) as channel:
                        channel.sendall(b"x")
                        assert channel.recv(2) == b"ok"
                accepted = True
            except ssl.SSLCertVerificationError:
                accepted = False
            assert accepted == expected
            outcomes.append(
                {"fixture_trusted": trusted, "hostname": hostname, "accepted": accepted}
            )
        thread.join(timeout=10)
        assert not thread.is_alive()
        return outcomes


def sql_checks():
    import mssql_python
    from azure.identity import ManagedIdentityCredential
    from cepio.integrations.microsoft.fabric_sql import FabricSqlSettings
    from mssql_python.connection_string_parser import _ConnectionStringParser

    info = mssql_python.get_native_provider_info()
    ctypes.CDLL(info["driver_path"])
    credential = ManagedIdentityCredential()
    credential.close()  # Construct only; do not request a token or contact Azure metadata.
    # Use the driver's actual parser without attempting any cloud authentication.
    settings = FabricSqlSettings(server="fixture.invalid", database="fixture")
    configuration = {"accepted": True}
    try:
        _ConnectionStringParser(validate_keywords=True)._parse(settings.connection_string)
    except Exception as error:
        configuration = {"accepted": False, "error_type": type(error).__name__, "error": str(error)}
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(8)
    port = listener.getsockname()[1]
    packets = []

    def receive_prelogin():
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                packet = connection.recv(4096)
                packets.append({"type": packet[0] if packet else None, "bytes": len(packet)})
        except TimeoutError:
            packets.append({"fixture_timeout": True})
        finally:
            listener.close()

    thread = threading.Thread(target=receive_prelogin, daemon=True)
    thread.start()
    failed = False
    try:
        # Probe native transport separately using the driver's supported timeout API.
        mssql_python.connect(
            f"Server=127.0.0.1,{port};Database=fixture;UID=fixture;PWD=unused-fixture;"
            "Encrypt=yes;TrustServerCertificate=no;",
            timeout=2,
        )
    except Exception as error:
        failed = True
        failure_type = type(error).__name__
        print(
            json.dumps(
                {
                    "sql_probe_error_type": failure_type,
                    "sql_probe_error": str(error),
                    "provider": info,
                }
            ),
            file=sys.stderr,
            flush=True,
        )
    thread.join(timeout=10)
    assert failed and not thread.is_alive() and packets and packets[0].get("type") == 0x12
    return {
        "provider": info,
        "tds_prelogin": packets,
        "closed_peer_rejected": failed,
        "failure_type": failure_type,
        "authenticated_sql_query_tested": False,
        "cepio_connection_configuration": configuration,
    }


def offline(variant):
    assert os.getuid() != 0
    manifest = json.loads(
        Path("/usr/local/share/cepio/base-evaluation-minimization.json").read_text()
    )
    assert (
        hashlib.sha256(Path(manifest["inventory"]).read_bytes()).hexdigest()
        == manifest["inventory_sha256"]
    )
    assert all(not Path(p).exists() and not Path(p).is_symlink() for p in manifest["removed_paths"])
    assert not Path("/bin/busybox").exists()
    assert Path("/bin/sh").resolve() == Path(manifest["replaced_shell"]["target"])
    for folder in ("/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin"):
        for p in Path(folder).iterdir():
            if p.is_file():
                assert hashlib.sha256(p.read_bytes()).hexdigest() != manifest["busybox_sha256"]
    for command in ("busybox", "mount", "umount", "nsenter", "unshare", "setpriv", "su", "login"):
        result = subprocess.run(["sh", "-c", f"command -v {command}"], capture_output=True)
        assert result.returncode != 0, command
    assert (
        subprocess.check_output(
            ["sh", "-c", 'printf "%s" "${PORT:-8000}"'],
            env=dict(os.environ, PORT="18081"),
            text=True,
        )
        == "18081"
    )
    for package in ("pip", "ensurepip"):
        assert importlib.util.find_spec(package) is None
    database = "/data/alpine-probe.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("create table fixture (value text)")
        connection.execute("insert into fixture values (?)", ("preserved",))
    result = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "import sqlite3; print(sqlite3.connect('/data/alpine-probe.sqlite').execute('select value from fixture').fetchone()[0])",
        ],
        text=True,
    )
    assert result.strip() == "preserved"
    report = {
        "hardening_passed": True,
        "sqlite_reopen_passed": True,
        "tls": tls_checks(),
        "uid": os.getuid(),
        "busybox_aliases_removed": manifest["busybox_aliases_removed"],
    }
    if variant == "integrations":
        from opentelemetry import context

        token = context.attach(context.set_value("cepio-fixture", "preserved"))
        assert context.get_value("cepio-fixture") == "preserved"
        context.detach(token)
        report["opentelemetry_context"] = True
        report["sql"] = sql_checks()
    else:
        assert importlib.util.find_spec("mssql_python") is None
    return report


def online():
    # Public metadata only: no tenant credentials, token request, inference or resource API.
    url = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
    assert socket.getaddrinfo("login.microsoftonline.com", 443)
    with urllib.request.urlopen(url, timeout=20, context=ssl.create_default_context()) as response:
        assert response.status == 200
        metadata = json.load(response)
    assert metadata["jwks_uri"].startswith("https://login.microsoftonline.com/")
    return {
        "public_microsoft_dns_https": True,
        "status": 200,
        "url": url,
        "credential_or_token_request": False,
    }


if __name__ == "__main__":
    mode = sys.argv[1]
    result = online() if mode == "online" else sql_checks() if mode == "sql" else offline(mode)
    print(json.dumps(result, sort_keys=True))
