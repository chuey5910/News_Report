"""CHUEY-Server LINE group relay — webhook เก็บ group ID + endpoint push ข่าวเข้ากลุ่ม

ทำไมต้องมีตัวนี้: หน้าเว็บ/pipeline หลักเป็น static (GitHub Pages) ไม่มี backend จึงส่งข่าว
ได้แค่แบบ Broadcast (ถึง "เพื่อน" ของ OA รายคน) ส่งเข้ากลุ่ม LINE ไม่ได้ เพราะการส่งเข้ากลุ่ม
ต้องใช้ Push API แบบระบุ groupId และ groupId จะรู้ได้ก็ต่อเมื่อมี webhook คอยดักตอน OA
ถูกเชิญเข้ากลุ่ม/มีคนพิมพ์ในกลุ่ม บริการนี้จึงรันบน CHUEY-Server (ต้องเปิด public + HTTPS)
เพื่อทำสองหน้าที่:

  POST /line/webhook  — รับ event จาก LINE, ตรวจลายเซ็น (X-Line-Signature), แล้ว
                        เพิ่ม/ลบ groupId ลงไฟล์ groups.json ตาม event join/leave/message
  POST /notify        — ให้ pipeline หลัก (GitHub Actions) เรียกเข้ามาพร้อม message ของ LINE
                        โดยแนบ bearer token; บริการจะ push ข้อความนั้นไปยังทุกกลุ่มที่เก็บไว้
  GET  /health        — health check (200 ok)

ออกแบบให้พึ่งพา Python 3 stdlib ล้วน (ไม่ต้อง pip install อะไรเลย) เพื่อให้ deploy บน
เซิร์ฟเวอร์อะไรก็ได้ ตั้งค่าทั้งหมดผ่าน environment variable (ดู README.md ในโฟลเดอร์นี้)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger("chuey_line_server")

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
DEFAULT_GROUPS_STORE_PATH = "groups.json"
DEFAULT_PORT = 8080
# LINE จำกัด 5 message object ต่อการเรียก push หนึ่งครั้ง
MAX_MESSAGES_PER_PUSH = 5
# body ที่ใหญ่กว่านี้ถือว่าผิดปกติ ปฏิเสธทิ้งเพื่อกัน memory abuse
MAX_BODY_BYTES = 256 * 1024


def verify_signature(body: bytes, signature: str | None, channel_secret: str) -> bool:
    """ตรวจ X-Line-Signature = base64(HMAC-SHA256(channel_secret, body)) แบบ constant-time"""
    if not signature:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


class GroupStore:
    """เก็บรายการ groupId ที่ OA อยู่ ลงไฟล์ JSON (thread-safe, ไม่ต้องใช้ DB)"""

    def __init__(self, path: str | Path = DEFAULT_GROUPS_STORE_PATH) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()

    def _read(self) -> set[str]:
        if not self._path.exists():
            return set()
        try:
            with open(self._path, encoding="utf-8") as f:
                return set(json.load(f))
        except (OSError, ValueError):
            logger.warning("groups store unreadable, treating as empty: %s", self._path)
            return set()

    def _write(self, groups: set[str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(groups), f, ensure_ascii=False)
        tmp.replace(self._path)  # atomic

    def add(self, group_id: str) -> bool:
        with self._lock:
            groups = self._read()
            if group_id in groups:
                return False
            groups.add(group_id)
            self._write(groups)
            logger.info("registered group %s (total %d)", group_id, len(groups))
            return True

    def remove(self, group_id: str) -> bool:
        with self._lock:
            groups = self._read()
            if group_id not in groups:
                return False
            groups.discard(group_id)
            self._write(groups)
            logger.info("removed group %s (total %d)", group_id, len(groups))
            return True

    def list(self) -> list[str]:
        with self._lock:
            return sorted(self._read())


def extract_group_updates(events: list[dict]) -> tuple[set[str], set[str]]:
    """แปลง LINE webhook events -> (กลุ่มที่ต้องเพิ่ม, กลุ่มที่ต้องลบ)

    เพิ่ม: OA ถูกเชิญเข้ากลุ่ม (join) หรือมีข้อความ/สมาชิกใหม่ในกลุ่มที่ OA อยู่ (message/
          memberJoined) — เก็บ groupId ไว้ได้แม้ OA เคยอยู่ก่อนเปิดใช้ webhook
    ลบ:  OA ถูกเชิญออก/ออกจากกลุ่ม (leave)
    """
    to_add: set[str] = set()
    to_remove: set[str] = set()
    for event in events:
        source = event.get("source") or {}
        if source.get("type") != "group":
            continue
        group_id = source.get("groupId")
        if not group_id:
            continue
        event_type = event.get("type")
        if event_type == "leave":
            to_remove.add(group_id)
        elif event_type in ("join", "message", "memberJoined", "postback"):
            to_add.add(group_id)
    return to_add, to_remove


def push_to_group(messages: list[dict], group_id: str, token: str, *, timeout: int = 15) -> None:
    payload = json.dumps({"to": group_id, "messages": messages[:MAX_MESSAGES_PER_PUSH]}).encode("utf-8")
    request = urllib.request.Request(
        LINE_PUSH_URL,
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"LINE push failed for {group_id}: {response.status}")


def push_to_all(messages: list[dict], group_ids: list[str], token: str) -> tuple[int, int]:
    """push ให้ครบทุกกลุ่ม — กลุ่มไหนพลาดก็ข้ามไปทำกลุ่มอื่นต่อ คืน (สำเร็จ, ล้มเหลว)"""
    ok = 0
    failed = 0
    for group_id in group_ids:
        try:
            push_to_group(messages, group_id, token)
            ok += 1
        except Exception:
            logger.exception("failed to push to group %s", group_id)
            failed += 1
    return ok, failed


class _Config:
    def __init__(self) -> None:
        self.channel_secret = os.environ.get("LINE_CHANNEL_SECRET", "")
        self.channel_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.notify_token = os.environ.get("CHUEY_SERVER_TOKEN", "")
        self.store = GroupStore(os.environ.get("GROUPS_STORE_PATH", DEFAULT_GROUPS_STORE_PATH))
        self.port = int(os.environ.get("PORT", DEFAULT_PORT))


def make_handler(config: _Config) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ChueyLineRelay/1.0"

        def _send(self, status: int, body: dict) -> None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_body(self) -> bytes | None:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                return None
            return self.rfile.read(length)

        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            if self.path == "/health":
                self._send(200, {"status": "ok", "groups": len(config.store.list())})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/line/webhook":
                self._handle_webhook()
            elif self.path == "/notify":
                self._handle_notify()
            else:
                self._send(404, {"error": "not found"})

        def _handle_webhook(self) -> None:
            body = self._read_body()
            if body is None:
                self._send(400, {"error": "bad request"})
                return
            if not config.channel_secret or not verify_signature(
                body, self.headers.get("X-Line-Signature"), config.channel_secret
            ):
                self._send(403, {"error": "invalid signature"})
                return
            try:
                events = json.loads(body).get("events", [])
            except ValueError:
                self._send(400, {"error": "invalid json"})
                return
            to_add, to_remove = extract_group_updates(events)
            for group_id in to_add:
                config.store.add(group_id)
            for group_id in to_remove:
                config.store.remove(group_id)
            self._send(200, {"ok": True})  # ต้องตอบ 200 เสมอ ไม่งั้น LINE จะ retry

        def _handle_notify(self) -> None:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {config.notify_token}"
            if not config.notify_token or not hmac.compare_digest(auth, expected):
                self._send(401, {"error": "unauthorized"})
                return
            body = self._read_body()
            if body is None:
                self._send(400, {"error": "bad request"})
                return
            try:
                data = json.loads(body)
            except ValueError:
                self._send(400, {"error": "invalid json"})
                return
            messages = data.get("messages")
            if not isinstance(messages, list) or not messages:
                self._send(400, {"error": "messages required"})
                return
            groups = config.store.list()
            if not groups:
                self._send(200, {"ok": True, "pushed": 0, "note": "no groups registered"})
                return
            if not config.channel_token:
                self._send(500, {"error": "LINE_CHANNEL_ACCESS_TOKEN not set"})
                return
            ok, failed = push_to_all(messages, groups, config.channel_token)
            self._send(200, {"ok": True, "pushed": ok, "failed": failed})

        def log_message(self, fmt: str, *args) -> None:  # เงียบ access log ตาม stdlib default
            logger.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = _Config()
    missing = [
        name
        for name, value in [
            ("LINE_CHANNEL_SECRET", config.channel_secret),
            ("LINE_CHANNEL_ACCESS_TOKEN", config.channel_token),
            ("CHUEY_SERVER_TOKEN", config.notify_token),
        ]
        if not value
    ]
    if missing:
        logger.warning("missing env vars (some endpoints will refuse requests): %s", ", ".join(missing))

    handler = make_handler(config)
    server = ThreadingHTTPServer(("0.0.0.0", config.port), handler)
    logger.info("CHUEY LINE relay listening on :%d (groups store: %s)", config.port, config.store._path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
