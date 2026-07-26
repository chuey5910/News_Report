import base64
import hashlib
import hmac
import json
from unittest.mock import patch

import pytest

from server.chuey_line_server import (
    GroupStore,
    extract_group_updates,
    push_to_all,
    verify_signature,
)


def _sign(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_verify_signature_accepts_valid_and_rejects_tampered():
    secret = "s3cr3t"
    body = b'{"events":[]}'
    good = _sign(body, secret)

    assert verify_signature(body, good, secret) is True
    assert verify_signature(body, good, "wrong-secret") is False
    assert verify_signature(b'{"events":[1]}', good, secret) is False
    assert verify_signature(body, None, secret) is False


def test_group_store_add_remove_list_and_persist(tmp_path):
    path = tmp_path / "groups.json"
    store = GroupStore(path)

    assert store.list() == []
    assert store.add("G1") is True
    assert store.add("G1") is False  # ซ้ำ ไม่เพิ่มรอบสอง
    assert store.add("G2") is True
    assert store.list() == ["G1", "G2"]

    # โหลดใหม่จากไฟล์เดิมต้องได้ค่าเดิม (persist จริง)
    assert GroupStore(path).list() == ["G1", "G2"]

    assert store.remove("G1") is True
    assert store.remove("G1") is False
    assert store.list() == ["G2"]


def test_group_store_treats_corrupt_file_as_empty(tmp_path):
    path = tmp_path / "groups.json"
    path.write_text("not json", encoding="utf-8")

    store = GroupStore(path)
    assert store.list() == []
    assert store.add("G1") is True


def test_extract_group_updates_maps_events():
    events = [
        {"type": "join", "source": {"type": "group", "groupId": "G_join"}},
        {"type": "message", "source": {"type": "group", "groupId": "G_msg"}},
        {"type": "leave", "source": {"type": "group", "groupId": "G_leave"}},
        {"type": "message", "source": {"type": "user", "userId": "U1"}},  # ไม่ใช่กลุ่ม -> ข้าม
        {"type": "join", "source": {"type": "group"}},  # ไม่มี groupId -> ข้าม
    ]

    to_add, to_remove = extract_group_updates(events)

    assert to_add == {"G_join", "G_msg"}
    assert to_remove == {"G_leave"}


def test_push_to_all_counts_success_and_failure():
    calls = []

    def fake_push(messages, group_id, token):
        calls.append(group_id)
        if group_id == "G_bad":
            raise RuntimeError("boom")

    with patch("server.chuey_line_server.push_to_group", side_effect=fake_push):
        ok, failed = push_to_all([{"type": "text", "text": "hi"}], ["G1", "G_bad", "G2"], "tok")

    assert (ok, failed) == (2, 1)
    assert calls == ["G1", "G_bad", "G2"]
