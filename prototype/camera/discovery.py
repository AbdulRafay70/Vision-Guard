"""
VisionGuard — Device discovery & stream auto-detection
======================================================

Turns "IP address + username + password" into working stream URLs for
standalone IP / WiFi cameras and multi-channel DVR / NVR recorders.

Detection order for a device:
  1. ONVIF (GetCapabilities → GetProfiles → GetStreamUri). The device reports its
     own exact RTSP URLs; on DVR/NVRs every channel is a profile.
  2. Brand URL templates (Hikvision, Dahua/CP Plus/Imou, Uniview, XMeye, TVT,
     Reolink, Tapo, Ezviz, V380, Yoosee, CamHi, Axis, Hanwha, generic …).

Each candidate is checked with a raw RTSP DESCRIBE handshake (Digest/Basic auth),
which answers in milliseconds: 200 = path and credentials good, 401 = wrong
credentials, 404 = wrong path. Only the winners are opened with OpenCV to grab
a verification snapshot.

Also: LAN discovery via ONVIF WS-Discovery multicast plus a TCP port sweep.

Pure standard library; OpenCV is only needed for snapshots.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import logging
import os
import re
import secrets
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

RTSP_TIMEOUT = 3.0
ONVIF_PORTS = [80, 8000, 8080, 8899, 2020, 5000, 888, 10080]
RTSP_PORTS = [554, 8554, 10554, 5543, 88]

# ── Brand stream templates ────────────────────────────────────────────────
# {ch} = channel number (1-based), {ch2} = zero-padded 2 digits, {ch0} = 0-based,
# {sub} = 0 main / 1 sub stream, {user}/{pw} = URL-encoded credentials.
BRANDS: Dict[str, Dict] = {
    "hikvision": {
        "label": "Hikvision / HiLook / Annke / Ezviz (DVR, NVR, IP)",
        "rtsp": ["/Streaming/Channels/{ch}0{sub1}", "/h264/ch{ch}/{main_sub}/av_stream", "/ISAPI/Streaming/channels/{ch}0{sub1}"],
        "ports": [8000],
    },
    "dahua": {
        "label": "Dahua / CP Plus / Imou / Amcrest / Lorex",
        "rtsp": ["/cam/realmonitor?channel={ch}&subtype={sub}"],
        "ports": [37777],
    },
    "uniview": {"label": "Uniview (UNV)", "rtsp": ["/unicast/c{ch}/s{sub}/live", "/media/video{ch}"], "ports": []},
    "xmeye": {
        "label": "XMeye / Sofia / generic Chinese DVR & NVR",
        "rtsp": ["/user={user}&password={pw}&channel={ch}&stream={sub}.sdp?", "/user={user}_password={pw}_channel={ch}_stream={sub}.sdp"],
        "ports": [34567],
    },
    "tvt": {"label": "TVT / Provision", "rtsp": ["/chID={ch}&streamType={main_sub}"], "ports": [6036]},
    "reolink": {"label": "Reolink", "rtsp": ["/h264Preview_{ch2}_{main_sub}", "/Preview_{ch2}_{main_sub}"], "ports": [9000]},
    "tapo": {"label": "TP-Link Tapo / VIGI (WiFi)", "rtsp": ["/stream{sub1}"], "ports": [2020]},
    "ezviz": {"label": "Ezviz (WiFi) — password is the verification code", "rtsp": ["/H.264", "/h264/ch1/{main_sub}/av_stream", "/Streaming/Channels/10{sub1}"], "ports": []},
    "v380": {"label": "V380 / V380 Pro (WiFi)", "rtsp": ["/live/ch00_{sub}", "/live/ch0{ch0}_{sub}"], "ports": [8800]},
    "yoosee": {"label": "Yoosee / Jortan (WiFi)", "rtsp": ["/onvif1", "/onvif2"], "ports": []},
    "camhi": {"label": "CamHi / HiChip (WiFi)", "rtsp": ["/{ch}{sub1}", "/1{sub1}"], "ports": []},
    "axis": {"label": "Axis", "rtsp": ["/axis-media/media.amp?camera={ch}"], "ports": []},
    "hanwha": {"label": "Hanwha / Samsung Wisenet", "rtsp": ["/profile{ch}/media.smp", "/{ch0}/profile2/media.smp"], "ports": [4520]},
    "generic": {
        "label": "Other / unknown brand",
        "rtsp": ["/live", "/stream1", "/live/ch{ch}", "/h264", "/live.sdp", "/video1", "/11", "/ch{ch}/main", "/onvif1", "/media/video1", "/0", "/"],
        "ports": [],
    },
}

# Plain HTTP MJPEG endpoints used by many cheap WiFi cameras and phone apps
HTTP_TEMPLATES = ["/video", "/video.mjpg", "/mjpg/video.mjpg", "/videostream.cgi?user={user}&pwd={pw}",
                  "/cgi-bin/mjpg/video.cgi", "/mjpeg", "/stream.mjpg"]

# Port fingerprints for discovery
PORT_HINTS = {8000: "hikvision", 37777: "dahua", 34567: "xmeye", 6036: "tvt", 9000: "reolink", 2020: "tapo", 8800: "v380", 4520: "hanwha"}


@dataclass
class StreamCandidate:
    url: str
    channel: int = 1
    source: str = "template"          # "onvif" or "template"
    brand: str = ""
    profile: str = ""
    status: int = 0                   # RTSP DESCRIBE status
    note: str = ""


@dataclass
class ProbeResult:
    ip: str
    reachable: bool = False
    open_ports: List[int] = field(default_factory=list)
    brand: str = ""
    model: str = ""
    manufacturer: str = ""
    onvif: bool = False
    auth_failed: bool = False
    streams: List[Dict] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────

def _enc(s: str) -> str:
    return quote(s or "", safe="")


def with_credentials(url: str, user: str, pw: str) -> str:
    """Insert (or replace) credentials in an rtsp/http URL."""
    if not user:
        return url
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{_enc(user)}:{_enc(pw)}@{host}" + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def mask_url(url: str) -> str:
    return re.sub(r"(://)([^/@:]+):([^/@]+)@", r"\1\2:•••••@", url)


def tcp_open(ip: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def expand_template(path: str, ch: int, sub: int, user: str, pw: str) -> str:
    return path.format(
        ch=ch, ch2=f"{ch:02d}", ch0=ch - 1, sub=sub, sub1=sub + 1,
        main_sub="main" if sub == 0 else "sub", user=_enc(user), pw=_enc(pw),
    )


# ── RTSP DESCRIBE handshake (with Basic / Digest auth) ────────────────────

def _parse_auth_header(value: str) -> Tuple[str, Dict[str, str]]:
    scheme, _, rest = value.partition(" ")
    params = dict(re.findall(r'(\w+)="?([^",]*)"?', rest))
    return scheme.lower(), params


def rtsp_describe(url: str, user: str = "", pw: str = "", timeout: float = RTSP_TIMEOUT) -> Tuple[int, str]:
    """
    Send RTSP DESCRIBE and return (status_code, info). 0 = no RTSP answer.
    Credentials in the URL are ignored on the wire (sent as auth headers instead).
    """
    parts = urlsplit(url)
    host, port = parts.hostname, parts.port or 554
    if parts.username and not user:
        user = urllib.request.unquote(parts.username)
        pw = urllib.request.unquote(parts.password or "")
    clean = urlunsplit((parts.scheme, f"{host}:{port}", parts.path or "/", parts.query, ""))

    def send(sock, cseq, auth=None):
        lines = [f"DESCRIBE {clean} RTSP/1.0", f"CSeq: {cseq}", "Accept: application/sdp", "User-Agent: VisionGuard"]
        if auth:
            lines.append(f"Authorization: {auth}")
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        data = b""
        deadline = time.monotonic() + timeout
        while b"\r\n\r\n" not in data and time.monotonic() < deadline:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1", "replace")
        m = re.match(r"RTSP/1\.\d (\d{3})", head)
        headers = {}
        for line in head.split("\r\n")[1:]:
            k, _, v = line.partition(":")
            headers.setdefault(k.strip().lower(), []).append(v.strip())
        return (int(m.group(1)) if m else 0), headers, head

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            code, headers, _ = send(sock, 1)
            if code != 401 or not user:
                return code, "" if code else "No RTSP response"
            challenges = headers.get("www-authenticate", [])
            digest = next((c for c in challenges if c.lower().startswith("digest")), None)
            if digest:
                _, p = _parse_auth_header(digest)
                realm, nonce = p.get("realm", ""), p.get("nonce", "")
                ha1 = hashlib.md5(f"{user}:{realm}:{pw}".encode()).hexdigest()
                ha2 = hashlib.md5(f"DESCRIBE:{clean}".encode()).hexdigest()
                resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
                auth = f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{clean}", response="{resp}"'
            else:
                auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
            code, _, _ = send(sock, 2, auth)
            return code, ""
    except socket.timeout:
        return 0, "Timed out"
    except OSError as e:
        return 0, str(e)


def http_stream_ok(url: str, timeout: float = RTSP_TIMEOUT) -> Tuple[int, str]:
    """Check an HTTP MJPEG/JPEG endpoint. Returns (status, content-type)."""
    parts = urlsplit(url)
    req_url = urlunsplit((parts.scheme, f"{parts.hostname}:{parts.port or 80}", parts.path, parts.query, ""))
    req = urllib.request.Request(req_url)
    if parts.username:
        token = base64.b64encode(f"{urllib.request.unquote(parts.username)}:{urllib.request.unquote(parts.password or '')}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (OSError, ValueError):
        return 0, ""


# ── ONVIF (minimal SOAP client with WS-Security UsernameToken) ────────────

def _wsse(user: str, pw: str) -> str:
    if not user:
        return ""
    nonce = secrets.token_bytes(16)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    digest = base64.b64encode(hashlib.sha1(nonce + created.encode() + pw.encode()).digest()).decode()
    return (
        '<s:Header><Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
        f"<UsernameToken><Username>{user}</Username>"
        f'<Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>'
        f'<Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{base64.b64encode(nonce).decode()}</Nonce>'
        f'<Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>'
        "</UsernameToken></Security></s:Header>"
    )


def _soap(url: str, body: str, user: str, pw: str, timeout: float = 4.0) -> ET.Element:
    envelope = ('<?xml version="1.0" encoding="UTF-8"?><s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
                'xmlns:tds="http://www.onvif.org/ver10/device/wsdl" xmlns:trt="http://www.onvif.org/ver10/media/wsdl" '
                f'xmlns:tt="http://www.onvif.org/ver10/schema">{_wsse(user, pw)}<s:Body>{body}</s:Body></s:Envelope>')
    req = urllib.request.Request(url, data=envelope.encode(), headers={"Content-Type": "application/soap+xml; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return ET.fromstring(r.read())
    except urllib.error.HTTPError as e:
        payload = e.read()
        text = payload.decode("utf-8", "replace").lower()
        if e.code in (400, 401, 500) and ("notauthorized" in text or "sender" in text and "auth" in text or e.code == 401):
            raise PermissionError("ONVIF authentication failed")
        raise


def _find_all(root: ET.Element, local: str) -> List[ET.Element]:
    return [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == local]


def _text(root: ET.Element, local: str) -> str:
    for el in _find_all(root, local):
        if el.text and el.text.strip():
            return el.text.strip()
    return ""


def onvif_streams(ip: str, port: int, user: str, pw: str, sub: int = 0) -> Dict:
    """Return {"manufacturer","model","streams":[(channel, profile, uri)]} via ONVIF."""
    device_url = f"http://{ip}:{port}/onvif/device_service"
    info = {"manufacturer": "", "model": "", "streams": []}
    try:
        root = _soap(device_url, "<tds:GetDeviceInformation/>", user, pw)
        info["manufacturer"] = _text(root, "Manufacturer")
        info["model"] = _text(root, "Model")
    except PermissionError:
        raise
    except Exception:
        pass
    caps = _soap(device_url, '<tds:GetCapabilities><tds:Category>Media</tds:Category></tds:GetCapabilities>', user, pw)
    media_url = ""
    for m in _find_all(caps, "Media"):
        media_url = _text(m, "XAddr") or media_url
    media_url = media_url or f"http://{ip}:{port}/onvif/media_service"
    # Some devices report an internal address; keep the path but use the address we reached
    mp = urlsplit(media_url)
    media_url = urlunsplit(("http", f"{ip}:{mp.port or port}", mp.path, "", ""))

    profiles = _soap(media_url, "<trt:GetProfiles/>", user, pw)
    entries = []
    for prof in _find_all(profiles, "Profiles"):
        token = prof.get("token", "")
        name = _text(prof, "Name") or token
        src = ""
        for vsc in _find_all(prof, "VideoSourceConfiguration"):
            src = _text(vsc, "SourceToken") or src
        width = 0
        for res in _find_all(prof, "Resolution"):
            try:
                width = max(width, int(_text(res, "Width") or 0))
            except ValueError:
                pass
        entries.append((token, name, src or token, width))

    # One stream per video source (= channel): highest resolution for main, lowest for sub
    by_source: Dict[str, List[Tuple[str, str, int]]] = {}
    for token, name, src, width in entries:
        by_source.setdefault(src, []).append((token, name, width))
    for idx, (src, profs) in enumerate(by_source.items(), start=1):
        profs.sort(key=lambda p: -p[2])
        token, name, _ = profs[0] if sub == 0 or len(profs) == 1 else profs[-1]
        body = ('<trt:GetStreamUri><trt:StreamSetup><tt:Stream>RTP-Unicast</tt:Stream><tt:Transport><tt:Protocol>RTSP</tt:Protocol>'
                f'</tt:Transport></trt:StreamSetup><trt:ProfileToken>{token}</trt:ProfileToken></trt:GetStreamUri>')
        try:
            uri = _text(_soap(media_url, body, user, pw), "Uri")
        except Exception as e:
            logger.debug("[ONVIF] GetStreamUri failed for %s: %s", token, e)
            continue
        if uri:
            up = urlsplit(uri)
            uri = urlunsplit((up.scheme, f"{ip}:{up.port or 554}", up.path, up.query, ""))  # fix NAT/internal IPs
            info["streams"].append((idx, name, uri))
    return info


def ws_discovery(timeout: float = 2.5) -> Dict[str, Dict]:
    """ONVIF WS-Discovery multicast probe. Returns {ip: {"xaddrs": [...], "scopes": str}}."""
    msg = ('<?xml version="1.0" encoding="UTF-8"?><e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
           'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
           'xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><e:Header>'
           f'<w:MessageID>uuid:{uuid.uuid4()}</w:MessageID><w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
           '<w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>'
           '<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>')
    found: Dict[str, Dict] = {}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(0.5)
        sock.sendto(msg.encode(), ("239.255.255.250", 3702))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            try:
                root = ET.fromstring(data)
            except ET.ParseError:
                continue
            found[addr[0]] = {"xaddrs": _text(root, "XAddrs").split(), "scopes": _text(root, "Scopes")}
        sock.close()
    except OSError as e:
        logger.debug("[DISCOVERY] WS-Discovery unavailable: %s", e)
    return found


def local_subnets() -> List[ipaddress.IPv4Network]:
    """Best-effort /24 subnets of this host's IPv4 interfaces."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    nets = []
    for ip in ips:
        if ip.startswith("127."):
            continue
        nets.append(ipaddress.ip_network(f"{ip}/24", strict=False))
    return nets


def discover(subnet: Optional[str] = None, timeout: float = 2.5) -> List[Dict]:
    """Find cameras / recorders on the LAN: WS-Discovery + TCP sweep of camera ports."""
    results: Dict[str, Dict] = {}
    for ip, d in ws_discovery(timeout).items():
        results[ip] = {"ip": ip, "onvif": True, "ports": [], "brand": "", "scopes": d["scopes"]}

    nets = [ipaddress.ip_network(subnet, strict=False)] if subnet else local_subnets()
    hosts = [str(h) for n in nets for h in list(n.hosts())[:254]]
    scan_ports = sorted(set(RTSP_PORTS[:2] + [80] + list(PORT_HINTS)))

    def check(ip):
        open_ports = [p for p in scan_ports if tcp_open(ip, p, 0.35)]
        return ip, open_ports

    with ThreadPoolExecutor(max_workers=128) as pool:
        for ip, ports in pool.map(check, hosts):
            camera_like = any(p in ports for p in RTSP_PORTS) or any(p in PORT_HINTS for p in ports)
            if not camera_like and ip not in results:
                continue
            entry = results.setdefault(ip, {"ip": ip, "onvif": False, "ports": [], "brand": "", "scopes": ""})
            entry["ports"] = ports
    for entry in results.values():
        entry["brand"] = next((PORT_HINTS[p] for p in entry["ports"] if p in PORT_HINTS), "") or _brand_from_scopes(entry["scopes"])
    return sorted(results.values(), key=lambda e: tuple(int(x) for x in e["ip"].split(".")))


def _brand_from_scopes(scopes: str) -> str:
    s = (scopes or "").lower()
    for key in ("hikvision", "dahua", "uniview", "reolink", "tapo", "axis", "hanwha", "ezviz", "imou"):
        if key in s:
            return {"imou": "dahua"}.get(key, key)
    return ""


def _brand_from_text(text: str) -> str:
    t = (text or "").lower()
    pairs = [("hikvision", "hikvision"), ("hik", "hikvision"), ("ezviz", "hikvision"), ("dahua", "dahua"), ("cp plus", "dahua"),
             ("cpplus", "dahua"), ("imou", "dahua"), ("amcrest", "dahua"), ("uniview", "uniview"), ("reolink", "reolink"),
             ("tp-link", "tapo"), ("tapo", "tapo"), ("axis", "axis"), ("hanwha", "hanwha"), ("samsung", "hanwha"), ("xm", "xmeye")]
    for k, v in pairs:
        if k in t:
            return v
    return ""


# ── Snapshot (OpenCV) ─────────────────────────────────────────────────────

def snapshot(url: str, timeout_ms: int = 8000, max_width: int = 480) -> Tuple[bool, str, Dict]:
    """Open the stream, grab one frame. Returns (ok, base64 JPEG or error, info)."""
    try:
        import cv2
    except ImportError:
        return False, "OpenCV not installed", {}
    if url.startswith("rtsp"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|timeout;5000000"
    params = []
    if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
        params = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms, cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms]
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG, params) if params else cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            return False, "Stream did not open", {}
        frame = None
        for _ in range(5):  # skip possible grey/partial first frames
            ok, f = cap.read()
            if ok and f is not None:
                frame = f
        if frame is None:
            return False, "No video frames received", {}
        h, w = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        if w > max_width:
            frame = cv2.resize(frame, (max_width, int(h * max_width / w)))
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return True, base64.b64encode(buf.tobytes()).decode() if ok else "", {"width": w, "height": h, "fps": round(fps, 1)}
    finally:
        cap.release()


# ── One-shot device probe ─────────────────────────────────────────────────

def _template_candidates(ip: str, port: int, user: str, pw: str, brands: List[str], channel: int, sub: int) -> List[StreamCandidate]:
    out = []
    for b in brands:
        for path in BRANDS[b]["rtsp"]:
            url = f"rtsp://{ip}:{port}" + expand_template(path, channel, sub, user, pw)
            if not any(c.url == url for c in out):
                out.append(StreamCandidate(url=url, channel=channel, brand=b))
    return out


def probe_device(ip: str, user: str = "", pw: str = "", kind: str = "camera", brand: str = "auto",
                 rtsp_port: int = 0, http_port: int = 0, max_channels: int = 16, sub_stream: bool = False,
                 with_snapshots: bool = True) -> ProbeResult:
    """
    Detect every working stream on a camera or DVR/NVR in one call.
    kind: "camera" (single stream) or "dvr" (enumerate channels 1..max_channels).
    """
    ip = ip.strip()
    res = ProbeResult(ip=ip)
    sub = 1 if sub_stream else 0
    max_channels = max(1, min(int(max_channels or 1), 64)) if kind == "dvr" else 1

    # 1. Reachability & open ports
    port_list = sorted(set(([rtsp_port] if rtsp_port else []) + RTSP_PORTS + ([http_port] if http_port else []) + ONVIF_PORTS + list(PORT_HINTS)))
    with ThreadPoolExecutor(max_workers=len(port_list)) as pool:
        flags = list(pool.map(lambda p: tcp_open(ip, p), port_list))
    res.open_ports = [p for p, ok in zip(port_list, flags) if ok]
    res.reachable = bool(res.open_ports)
    if not res.reachable:
        res.messages.append(f"{ip} is not reachable on any camera port. Check the IP address, that the device is powered, "
                            "and that this server is on the same network / VLAN (or the port is forwarded).")
        return res
    rtsp_ports = [p for p in ([rtsp_port] if rtsp_port else []) + RTSP_PORTS if p in res.open_ports]
    hint = next((PORT_HINTS[p] for p in res.open_ports if p in PORT_HINTS), "")

    found: Dict[int, StreamCandidate] = {}

    # 2. ONVIF — exact URLs straight from the device
    onvif_ports = ([http_port] if http_port else []) + [p for p in ONVIF_PORTS if p in res.open_ports]
    for op in dict.fromkeys(onvif_ports):
        try:
            info = onvif_streams(ip, op, user, pw, sub)
        except PermissionError:
            res.auth_failed = True
            res.messages.append("ONVIF rejected the username/password.")
            break
        except Exception as e:
            logger.debug("[PROBE] ONVIF on %s:%d failed: %s", ip, op, e)
            continue
        res.onvif = True
        res.manufacturer, res.model = info["manufacturer"], info["model"]
        for ch, name, uri in info["streams"][:max_channels]:
            found[ch] = StreamCandidate(url=uri, channel=ch, source="onvif", profile=name, brand=_brand_from_text(res.manufacturer))
        if found:
            res.messages.append(f"ONVIF reported {len(found)} video channel(s).")
            break

    res.brand = (brand if brand not in ("", "auto") else "") or _brand_from_text(res.manufacturer) or hint

    # 3. Brand templates (if ONVIF is off or incomplete)
    if not found and rtsp_ports:
        order = ([res.brand] if res.brand in BRANDS else []) + [b for b in BRANDS if b not in (res.brand,)]
        if brand not in ("", "auto") and brand in BRANDS:
            order = [brand] + [b for b in order if b != brand]
        winner: Optional[StreamCandidate] = None
        template_used = ""
        for port in rtsp_ports:
            cands = _template_candidates(ip, port, user, pw, order, 1, sub)
            with ThreadPoolExecutor(max_workers=12) as pool:
                codes = list(pool.map(lambda c: rtsp_describe(c.url, user, pw)[0], cands))
            for c, code in zip(cands, codes):
                c.status = code
            ok = [c for c in cands if c.status == 200]
            if any(c.status == 401 for c in cands) and not ok:
                res.auth_failed = True
            if ok:
                # Keep template order (brand-specific first); a path that answers 200 is real
                winner = ok[0]
                template_used = next(path for path in BRANDS[winner.brand]["rtsp"]
                                     if f"rtsp://{ip}:{port}" + expand_template(path, 1, sub, user, pw) == winner.url)
                res.brand = res.brand or winner.brand
                break
        if winner:
            found[1] = winner
            if kind == "dvr" and "{ch" in template_used:
                chans = list(range(2, max_channels + 1))
                port = urlsplit(winner.url).port

                def check(ch):
                    url = f"rtsp://{ip}:{port}" + expand_template(template_used, ch, sub, user, pw)
                    return ch, url, rtsp_describe(url, user, pw)[0]

                with ThreadPoolExecutor(max_workers=8) as pool:
                    for ch, url, code in pool.map(check, chans):
                        if code == 200:
                            found[ch] = StreamCandidate(url=url, channel=ch, brand=winner.brand, status=200)
        elif res.auth_failed:
            res.messages.append("The device answered but rejected the username/password.")

    # 4. HTTP MJPEG fallback for simple WiFi cameras
    if not found:
        for hp in [p for p in ([http_port] if http_port else []) + [80, 8080, 81, 8081] if p in res.open_ports]:
            for path in HTTP_TEMPLATES:
                url = with_credentials(f"http://{ip}:{hp}" + expand_template(path, 1, 0, user, pw), user, pw)
                code, ctype = http_stream_ok(url)
                if code == 200 and ("multipart" in ctype or "image" in ctype or "video" in ctype):
                    found[1] = StreamCandidate(url=url, channel=1, source="http", note=ctype)
                    break
            if found:
                break

    if not found:
        if not res.auth_failed:
            res.messages.append("No stream path matched. Enable RTSP/ONVIF in the device's network settings, "
                                "or enter the stream URL manually.")
        return res

    # 5. Verify with a real frame + thumbnail (in parallel, limited)
    streams = sorted(found.values(), key=lambda c: c.channel)
    authed = [with_credentials(c.url, user, pw) if c.url.startswith("rtsp") and user and "@" not in c.url.split("//", 1)[1].split("/", 1)[0] else c.url
              for c in streams]

    def verify(i):
        if not with_snapshots:
            return i, (None, "", {})
        return i, snapshot(authed[i])

    with ThreadPoolExecutor(max_workers=4) as pool:
        verified = dict(pool.map(verify, range(len(streams))))
    for i, c in enumerate(streams):
        ok, img, info = verified[i]
        res.streams.append({
            "channel": c.channel,
            "url": authed[i],
            "url_masked": mask_url(authed[i]),
            "via": c.source,
            "profile": c.profile,
            "verified": ok,          # None = not checked
            "snapshot": img if ok else "",
            "error": "" if ok or ok is None else img,
            **({k: info[k] for k in ("width", "height", "fps")} if ok else {}),
        })
    good = sum(1 for s in res.streams if s["verified"])
    res.messages.append(f"Found {len(res.streams)} stream(s)" + (f", {good} verified with a live frame." if with_snapshots else "."))
    return res
