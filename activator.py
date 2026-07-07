import argparse
import http.server
import json
import os
import ssl
import subprocess
import sys
import tempfile
import socket
import re

HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
HOSTS_MARKER = "# Laragon License Activator"
REDIRECT_ENTRY = f"127.0.0.1 api.laragon.org {HOSTS_MARKER}"
SERVER_PORT = 443

LICENSE_KEY_PATTERN = re.compile(
    r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
    re.IGNORECASE
)

LICENSE_DATA = {
    "license_key": {
        "id": 999999,
        "status": "active",
        "key": "",
        "activation_limit": 999,
        "activation_usage": 1,
        "created_at": "2025-01-01T00:00:00.000000Z",
        "expires_at": None,
    },
    "instance": {
        "id": "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "",
        "created_at": "2025-01-01T00:00:00.000000Z",
    },
    "meta": {
        "store_id": 99999,
        "order_id": 99999,
        "order_item_id": 99999,
        "variant_id": 99999,
        "variant_name": "Perpetual",
        "product_id": 99999,
        "product_name": "Laragon",
        "customer_id": 99999,
        "customer_name": "Test User",
        "customer_email": "user@test.local",
    },
}


def build_activate_response(license_key, instance_name):
    import copy
    data = copy.deepcopy(LICENSE_DATA)
    data["license_key"]["key"] = license_key
    data["instance"]["name"] = instance_name
    return {
        "activated": True,
        "success": True,
        "error": None,
        "data": data,
    }


def build_validate_response(license_key, instance_id, machine_uuid):
    import copy
    data = copy.deepcopy(LICENSE_DATA)
    data["license_key"]["key"] = license_key
    if instance_id:
        data["instance"]["id"] = instance_id
    return {
        "valid": True,
        "success": True,
        "error": None,
        "data": data,
    }


def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0


def add_hosts_entry():
    with open(HOSTS_FILE, "r") as f:
        content = f.read()
    if HOSTS_MARKER in content:
        print("[*] Hosts entry already exists.")
        return
    with open(HOSTS_FILE, "a") as f:
        f.write(f"\n{REDIRECT_ENTRY}\n")
    print("[+] Added hosts redirect: api.laragon.org -> 127.0.0.1")


def remove_hosts_entry():
    with open(HOSTS_FILE, "r") as f:
        lines = f.readlines()
    filtered = [line for line in lines if HOSTS_MARKER not in line]
    with open(HOSTS_FILE, "w") as f:
        f.writelines(filtered)
    print("[+] Removed hosts redirect.")
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
    print("[+] DNS cache flushed.")


def generate_self_signed_cert(cert_dir):
    cert_file = os.path.join(cert_dir, "server.pem")
    key_file = os.path.join(cert_dir, "server.key")

    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file

    try:
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", key_file, "-out", cert_file,
                "-days", "365", "-nodes", "-batch",
                "-subj", "/CN=api.laragon.org",
                "-addext", "subjectAltName=DNS:api.laragon.org,DNS:localhost,IP:127.0.0.1",
            ],
            capture_output=True,
            check=True,
        )
        print("[+] Generated self-signed certificate for api.laragon.org")
    except FileNotFoundError:
        print("[!] openssl not found — generating cert with Python stdlib")
        _generate_cert_python(cert_file, key_file)
    except subprocess.CalledProcessError:
        print("[!] openssl failed — generating cert with Python stdlib")
        _generate_cert_python(cert_file, key_file)

    return cert_file, key_file


def _generate_cert_python(cert_file, key_file):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "api.laragon.org"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName('api.laragon.org'),
                    x509.DNSName('localhost'),
                    x509.IPAddress(__import__('ipaddress').ip_address('127.0.0.1')),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        print("[+] Generated self-signed certificate")
    except ImportError:
        print("[!] Install 'cryptography' package or add openssl to PATH.")
        print("    pip install cryptography")
        sys.exit(1)


class FakeLicenseHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _check_host_header(self):
        """Only respond to api.laragon.org, reject other hosts"""
        host = self.headers.get('Host', '').split(':')[0].lower()
        if host not in ('api.laragon.org', 'localhost', '127.0.0.1'):
            self.send_error(404, "Unknown host")
            return False
        return True

    def do_POST(self):
        if not self._check_host_header():
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace")

        print(f"\n{'='*60}")
        print(f"[>] {self.command} {self.path}")
        print(f"    Host: {self.headers.get('Host', '(none)')}")
        print(f"    Auth: {self.headers.get('Authorization', '(none)')}")
        print(f"    Body: {body}")

        try:
            request_data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            request_data = {}

        if "/v1/licenses/activate" in self.path:
            license_key = request_data.get("license_key", "UNKNOWN")
            instance_name = request_data.get("instance_name", "UNKNOWN")

            if not LICENSE_KEY_PATTERN.match(license_key):
                print(f"[!] Invalid license key format: {license_key}")
                self.send_error(400, "Invalid license key format")
                return

            response = build_activate_response(license_key, instance_name)
            print(f"[<] ACTIVATE -> key={license_key}, instance={instance_name}")

        elif "/v1/licenses/validate" in self.path:
            license_key = request_data.get("license_key", "UNKNOWN")
            instance_id = request_data.get("instance_id", "")
            machine_uuid = request_data.get("machine_uuid", "")

            if not LICENSE_KEY_PATTERN.match(license_key):
                print(f"[!] Invalid license key format: {license_key}")
                self.send_error(400, "Invalid license key format")
                return

            response = build_validate_response(license_key, instance_id, machine_uuid)
            print(f"[<] VALIDATE -> key={license_key}")

        else:
            print(f"[!] Unknown endpoint: {self.path}")
            self.send_error(404)
            return

        payload = json.dumps(response, separators=(',', ':')).encode()

        print(f"[<] Response ({len(payload)} bytes):")
        print(json.dumps(response, indent=2))
        print(f"{'='*60}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def do_GET(self):
        if not self._check_host_header():
            return

        # Only respond to api.laragon.org, not generic localhost requests
        host = self.headers.get('Host', '').split(':')[0].lower()
        if host != 'api.laragon.org':
            self.send_error(404, "This server only handles api.laragon.org requests")
            return

        payload = b"Fake api.laragon.org - Laragon License Activator\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def log_message(self, fmt, *args):
        pass

    def setup(self):
        self.connection = self.request
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()
        try:
            self.request.unwrap()
        except Exception:
            pass
        self.request.close()


class ProperHTTPServer(http.server.HTTPServer):
    def shutdown_request(self, request):
        try:
            request.shutdown(socket.SHUT_RDWR)
        except (OSError, AttributeError):
            pass
        self.close_request(request)

    def close_request(self, request):
        try:
            request.close()
        except (OSError, AttributeError):
            pass


def run_server(cert_dir):
    cert_file, key_file = generate_self_signed_cert(cert_dir)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_file, key_file)

    server = ProperHTTPServer(("0.0.0.0", SERVER_PORT), FakeLicenseHandler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f"\n[+] Fake license server running on https://0.0.0.0:{SERVER_PORT}")
    print(f"[+] Cert: {cert_file}")
    print()
    print("[+] INSTRUCTIONS:")
    print("    1. Open Laragon")
    print("    2. Go to the license")
    print("    3. Enter any license key in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    print("    4. Click 'Verify license'")
    print("    5. Watch this console for requests")
    print()
    print("[+] Waiting for requests... (Ctrl+C to stop)\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
        server.server_close()


def verify_dns():
    import socket
    try:
        ip = socket.gethostbyname("api.laragon.org")
        if ip == "127.0.0.1":
            print(f"[+] DNS check OK: api.laragon.org -> {ip}")
            return True
        else:
            print(f"[!] DNS check FAILED: api.laragon.org -> {ip} (expected 127.0.0.1)")
            print("    Try: ipconfig /flushdns")
            return False
    except socket.gaierror:
        print("[!] DNS check FAILED: cannot resolve api.laragon.org")
        return False


def check_port_available():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", SERVER_PORT))
        sock.close()
        return True
    except OSError:
        print(f"[!] Port {SERVER_PORT} is already in use!")
        print("    Check: netstat -ano | findstr :443")
        print("    Stop whatever is using port 443")
        sock.close()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Laragon License Activator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Add hosts entry and start fake server")
    group.add_argument("--server", action="store_true", help="Start fake server only (manual hosts edit)")
    group.add_argument("--cleanup", action="store_true", help="Remove hosts entry")
    args = parser.parse_args()

    if args.cleanup:
        if not is_admin():
            print("[!] Run as Administrator to modify hosts file.")
            sys.exit(1)
        remove_hosts_entry()
        return

    cert_dir = os.path.join(tempfile.gettempdir(), "laragon_activator_certs")
    os.makedirs(cert_dir, exist_ok=True)

    if args.setup:
        if not is_admin():
            print("[!] Run as Administrator to modify hosts file and bind port 443.")
            sys.exit(1)

        add_hosts_entry()
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
        print("[+] DNS cache flushed.")
        verify_dns()

        if not check_port_available():
            sys.exit(1)

        run_server(cert_dir)

    elif args.server:
        verify_dns()
        if not check_port_available():
            sys.exit(1)
        run_server(cert_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("  Laragon License Activator")
    print("=" * 60)
    main()