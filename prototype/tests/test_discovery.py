"""
Device auto-detection tests against fake RTSP and ONVIF servers on localhost.
Runs without cameras / OpenCV:  python -m pytest prototype/tests -q
"""
import hashlib
import re
import socket
import socketserver
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camera import discovery  # noqa: E402
from camera.discovery import probe_device, rtsp_describe, with_credentials  # noqa: E402

USER, PW, REALM, NONCE = "admin", "S3cret!", "IP Camera", "abc123"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FakeRTSP:
    """Minimal RTSP server: answers DESCRIBE with 401 → Digest-authenticated 200, or 404."""

    def __init__(self, valid_paths):
        self.valid = valid_paths
        self.port = free_port()
        fake = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                buf = b""
                while True:
                    try:
                        chunk = self.request.recv(4096)
                    except OSError:
                        return
                    if not chunk:
                        return
                    buf += chunk
                    while b"\r\n\r\n" in buf:
                        req, buf = buf.split(b"\r\n\r\n", 1)
                        self.request.sendall(fake.respond(req.decode()))

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", self.port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def respond(self, req):
        first = req.split("\r\n")[0]
        uri = first.split(" ")[1]
        cseq = re.search(r"CSeq: (\d+)", req).group(1)
        path = uri.split(f":{self.port}", 1)[1]
        auth = re.search(r"Authorization: (.*)", req)
        if not auth:
            return f'RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\nWWW-Authenticate: Digest realm="{REALM}", nonce="{NONCE}"\r\n\r\n'.encode()
        p = dict(re.findall(r'(\w+)="([^"]*)"', auth.group(1)))
        ha1 = hashlib.md5(f"{USER}:{REALM}:{PW}".encode()).hexdigest()
        ha2 = hashlib.md5(f"DESCRIBE:{p.get('uri')}".encode()).hexdigest()
        if p.get("username") != USER or p.get("response") != hashlib.md5(f"{ha1}:{NONCE}:{ha2}".encode()).hexdigest():
            return f"RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\nWWW-Authenticate: Digest realm=\"{REALM}\", nonce=\"{NONCE}\"\r\n\r\n".encode()
        code = "200 OK" if path in self.valid else "404 Not Found"
        return f"RTSP/1.0 {code}\r\nCSeq: {cseq}\r\nContent-Length: 0\r\n\r\n".encode()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeONVIF:
    """ONVIF device/media service reporting two video sources (main + sub profile each)."""

    def __init__(self, rtsp_port):
        self.port = free_port()
        rport = rtsp_port

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"])).decode()
                if "UsernameToken" not in body or f"<Username>{USER}</Username>" not in body:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"<Fault><Code><Value>Sender</Value><Subcode><Value>ter:NotAuthorized</Value></Subcode></Code></Fault>")
                    return
                if "GetDeviceInformation" in body:
                    xml = "<Manufacturer>HIKVISION</Manufacturer><Model>DS-7608NI</Model>"
                elif "GetCapabilities" in body:
                    xml = f"<Media><XAddr>http://10.0.0.99:{self.server.server_port}/onvif/Media</XAddr></Media>"
                elif "GetProfiles" in body:
                    xml = "".join(
                        f'<Profiles token="{t}"><Name>{t}</Name><VideoSourceConfiguration><SourceToken>{src}</SourceToken></VideoSourceConfiguration>'
                        f"<VideoEncoderConfiguration><Resolution><Width>{w}</Width><Height>{w * 9 // 16}</Height></Resolution></VideoEncoderConfiguration></Profiles>"
                        for t, src, w in [("main1", "VS1", 1920), ("sub1", "VS1", 640), ("main2", "VS2", 1920), ("sub2", "VS2", 640)])
                elif "GetStreamUri" in body:
                    token = re.search(r"<trt:ProfileToken>(\w+)</trt:ProfileToken>", body).group(1)
                    ch = token[-1]
                    # Internal address on purpose: the client must rewrite it to the reachable IP
                    xml = f"<Uri>rtsp://10.0.0.99:{rport}/Streaming/Channels/{ch}0{1 if token.startswith('main') else 2}</Uri>"
                else:
                    xml = ""
                data = f'<?xml version="1.0"?><Envelope><Body><R>{xml}</R></Body></Envelope>'.encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/soap+xml")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(autouse=True)
def isolate_ports(monkeypatch):
    # Only probe the fake servers' ports, never real well-known ports on the test host
    monkeypatch.setattr(discovery, "RTSP_PORTS", [])
    monkeypatch.setattr(discovery, "ONVIF_PORTS", [])
    monkeypatch.setattr(discovery, "PORT_HINTS", {})


def test_describe_digest_auth_and_paths():
    srv = FakeRTSP({"/stream1"})
    try:
        base = f"rtsp://127.0.0.1:{srv.port}"
        assert rtsp_describe(f"{base}/stream1", USER, PW)[0] == 200
        assert rtsp_describe(f"{base}/stream1", USER, "wrong")[0] == 401
        assert rtsp_describe(f"{base}/nope", USER, PW)[0] == 404
        # credentials embedded in the URL are used too
        assert rtsp_describe(with_credentials(f"{base}/stream1", USER, PW))[0] == 200
    finally:
        srv.close()


def test_dvr_channels_detected_from_brand_templates():
    paths = {f"/cam/realmonitor?channel={c}&subtype=0" for c in (1, 2, 3, 4)}
    srv = FakeRTSP(paths)
    try:
        r = probe_device("127.0.0.1", USER, PW, kind="dvr", rtsp_port=srv.port, max_channels=8, with_snapshots=False)
        assert r.reachable and not r.auth_failed
        assert r.brand == "dahua"
        assert [s["channel"] for s in r.streams] == [1, 2, 3, 4]
        assert all(s["url"].startswith(f"rtsp://admin:S3cret%21@127.0.0.1:{srv.port}/cam/realmonitor") for s in r.streams)
        assert "•" in r.streams[0]["url_masked"]
    finally:
        srv.close()


def test_wifi_camera_detected():
    srv = FakeRTSP({"/live/ch00_0"})  # V380-style
    try:
        r = probe_device("127.0.0.1", USER, PW, kind="camera", rtsp_port=srv.port, with_snapshots=False)
        assert len(r.streams) == 1 and r.streams[0]["url"].endswith("/live/ch00_0")
    finally:
        srv.close()


def test_wrong_password_reported():
    srv = FakeRTSP({"/stream1"})
    try:
        r = probe_device("127.0.0.1", USER, "bad", kind="camera", rtsp_port=srv.port, with_snapshots=False)
        assert r.auth_failed and not r.streams
        assert any("password" in m for m in r.messages)
    finally:
        srv.close()


def test_onvif_reports_channels_and_fixes_internal_ip():
    rtsp = FakeRTSP({"/Streaming/Channels/101", "/Streaming/Channels/201"})
    onvif = FakeONVIF(rtsp.port)
    try:
        r = probe_device("127.0.0.1", USER, PW, kind="dvr", rtsp_port=rtsp.port, http_port=onvif.port,
                         max_channels=16, with_snapshots=False)
        assert r.onvif and r.manufacturer == "HIKVISION" and r.brand == "hikvision"
        assert [s["channel"] for s in r.streams] == [1, 2]
        assert r.streams[0]["url"] == f"rtsp://admin:S3cret%21@127.0.0.1:{rtsp.port}/Streaming/Channels/101"
        assert r.streams[0]["via"] == "onvif"
    finally:
        onvif.close()
        rtsp.close()


def test_unreachable_device():
    r = probe_device("127.0.0.1", USER, PW, kind="camera", rtsp_port=free_port(), with_snapshots=False)
    assert not r.reachable and "not reachable" in r.messages[0]
