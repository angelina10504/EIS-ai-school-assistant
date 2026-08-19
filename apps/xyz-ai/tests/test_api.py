"""HTTP surface: auth, the chat endpoints, and REST parity with the graph's gate."""
from __future__ import annotations


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert len(body["languages"]) == 11


def test_login_rejects_bad_credentials(client):
    response = client.post(
        "/api/session/login", json={"email": "rahul@student.xyz.edu", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.text


def test_chat_requires_a_token(client):
    assert client.post("/api/chat", json={"session_id": "x", "message": "hi"}).status_code == 401


def test_chat_rejects_someone_elses_session(client, login):
    rahul = login("rahul@student.xyz.edu")
    priya = login("priya@student.xyz.edu")
    response = client.post(
        "/api/chat",
        json={"session_id": priya["session_id"], "message": "my attendance"},
        headers=rahul["headers"],
    )
    assert response.status_code == 404


def test_chat_roundtrip(client, login):
    rahul = login("rahul@student.xyz.edu")
    body = client.post(
        "/api/chat",
        json={"session_id": rahul["session_id"], "message": "What is my attendance?"},
        headers=rahul["headers"],
    ).json()
    assert body["intent"] == "view_attendance"
    assert body["data"]["student_name"] == "Rahul Verma"
    assert body["trace"][0] == "auth_resolver"
    assert body["trace"][-1] == "memory_writer"


def test_confirm_without_a_pending_offer_is_a_conflict(client, login):
    rahul = login("rahul@student.xyz.edu")
    response = client.post(
        "/api/chat/confirm", json={"session_id": rahul["session_id"]}, headers=rahul["headers"]
    )
    assert response.status_code == 409


def test_escalation_over_http(client, login):
    farah = login("farah@parent.xyz.edu")
    offer = client.post(
        "/api/chat",
        json={"session_id": farah["session_id"], "message": "I'm not satisfied, connect me to the teacher"},
        headers=farah["headers"],
    ).json()
    assert offer["requires_confirmation"] is True

    done = client.post(
        "/api/chat/confirm", json={"session_id": farah["session_id"]}, headers=farah["headers"]
    ).json()
    assert done["data"]["ok"] is True
    assert done["requires_confirmation"] is False


def test_declining_the_offer_writes_nothing(client, login):
    farah = login("farah@parent.xyz.edu")
    client.post(
        "/api/chat",
        json={"session_id": farah["session_id"], "message": "connect me to the teacher please"},
        headers=farah["headers"],
    )
    body = client.post(
        "/api/chat/confirm",
        json={"session_id": farah["session_id"], "confirm": False},
        headers=farah["headers"],
    ).json()
    assert body["data"]["kind"] == "escalation_cancelled"


def test_rest_attendance_respects_the_matrix(client, login):
    principal = login("principal@xyz.edu")
    rahul = login("rahul@student.xyz.edu")

    # The principal is denied individual records by the matrix, not by prompting.
    denied = client.get(f"/api/attendance/{rahul['user']['id']}", headers=principal["headers"])
    assert denied.status_code == 403

    allowed = client.get(f"/api/attendance/{rahul['user']['id']}", headers=rahul["headers"])
    assert allowed.status_code == 200
    assert allowed.json()["student_name"] == "Rahul Verma"


def test_rest_mark_attendance_is_teacher_only(client, login):
    parent = login("sunita@parent.xyz.edu")
    teacher = login("anita@teacher.xyz.edu")

    blocked = client.post(
        "/api/attendance/mark",
        json={"student_name": "Rahul Verma", "status": "present"},
        headers=parent["headers"],
    )
    assert blocked.status_code == 403

    ok = client.post(
        "/api/attendance/mark",
        json={"student_name": "Rahul Verma", "status": "late"},
        headers=teacher["headers"],
    )
    assert ok.status_code == 200 and ok.json()["status"] == "late"


def test_rest_analytics_is_principal_only(client, login):
    teacher = login("anita@teacher.xyz.edu")
    principal = login("principal@xyz.edu")
    assert client.get("/api/analytics/attendance", headers=teacher["headers"]).status_code == 403
    assert client.get("/api/analytics/attendance", headers=principal["headers"]).status_code == 200


def test_audit_endpoint_shows_only_your_own_rows(client, login):
    rahul = login("rahul@student.xyz.edu")
    client.post(
        "/api/chat",
        json={"session_id": rahul["session_id"], "message": "mark me present"},
        headers=rahul["headers"],
    )
    entries = client.get("/api/audit/recent", headers=rahul["headers"]).json()["entries"]
    assert any(e["allowed"] is False for e in entries)


def test_language_switch_persists(client, login):
    rahul = login("rahul@student.xyz.edu")
    body = client.post(
        "/api/session/language", json={"language": "hi"}, headers=rahul["headers"]
    ).json()
    assert body["preferred_language"] == "hi"
    client.post("/api/session/language", json={"language": "en"}, headers=rahul["headers"])


def test_unsupported_language_is_rejected(client, login):
    rahul = login("rahul@student.xyz.edu")
    response = client.post(
        "/api/session/language", json={"language": "fr"}, headers=rahul["headers"]
    )
    assert response.status_code == 400
