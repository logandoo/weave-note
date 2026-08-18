"""weave-note 安全修复验收测试（wave-2026-08-18）。

运行前提：weave-note 服务已在 127.0.0.1:8201 运行（scripts/start.sh）。
测试用例从 README API 表 + acceptance.md wave1 标准导出。
"""
import sys
import httpx

BASE = "http://127.0.0.1:8201"
USER = "test"
PASSWORD = "123456"


def login(client: httpx.Client) -> dict:
    r = client.post(f"{BASE}/api/auth/login", json={"username": USER, "password": PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_logout_invalidates_token(client: httpx.Client) -> None:
    token = login(client)["access_token"]
    r = client.get(f"{BASE}/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 200, "pre-logout /me should be 200"
    r = client.post(f"{BASE}/api/auth/logout", headers=auth_headers(token))
    assert r.status_code == 200, f"logout failed: {r.status_code}"
    r = client.get(f"{BASE}/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 401, f"post-logout /me should be 401, got {r.status_code}"


def test_other_token_still_valid_after_logout(client: httpx.Client) -> None:
    t1 = login(client)["access_token"]
    t2 = login(client)["access_token"]
    client.post(f"{BASE}/api/auth/logout", headers=auth_headers(t1))
    r1 = client.get(f"{BASE}/api/auth/me", headers=auth_headers(t1))
    assert r1.status_code == 401, f"logged-out token must be 401, got {r1.status_code}"
    r2 = client.get(f"{BASE}/api/auth/me", headers=auth_headers(t2))
    assert r2.status_code == 200, f"live token must stay 200, got {r2.status_code}"


def _create_note(client: httpx.Client, token: str, notebook_id: str, title: str) -> str:
    r = client.post(
        f"{BASE}/api/notes/notebooks/{notebook_id}/notes",
        headers=auth_headers(token),
        json={"title": title, "content": f"content-{title}"},
    )
    assert r.status_code in (200, 201), f"create note failed: {r.status_code} {r.text}"
    return r.json()["id"]


def test_search_percent_is_literal(client: httpx.Client) -> None:
    token = login(client)["access_token"]
    nb_id = client.get(f"{BASE}/api/notes/default-notebook", headers=auth_headers(token)).json()["id"]
    _create_note(client, token, nb_id, "进度 100% 完成")
    _create_note(client, token, nb_id, "普通笔记无百分号")
    r = client.get(f"{BASE}/api/notes/search", headers=auth_headers(token), params={"q": "%"})
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()]
    assert "进度 100% 完成" in titles, f"'%' must match literal percent notes, got {titles}"
    assert "普通笔记无百分号" not in titles, f"'%' must NOT match all notes, got {titles}"


def test_search_underscore_is_literal(client: httpx.Client) -> None:
    token = login(client)["access_token"]
    nb_id = client.get(f"{BASE}/api/notes/default-notebook", headers=auth_headers(token)).json()["id"]
    _create_note(client, token, nb_id, "命名规范 a_b_c")
    _create_note(client, token, nb_id, "命名规范 abc")
    r = client.get(f"{BASE}/api/notes/search", headers=auth_headers(token), params={"q": "_"})
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()]
    assert "命名规范 a_b_c" in titles, f"'_' must match literal underscore, got {titles}"
    assert "命名规范 abc" not in titles, f"'_' must not wildcard, got {titles}"


def test_cors_star_forces_no_credentials(client: httpx.Client) -> None:
    r = client.options(
        f"{BASE}/api/auth/login",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 400, 405), f"preflight failed: {r.status_code}"
    aco = r.headers.get("access-control-allow-origin", "")
    acc = r.headers.get("access-control-allow-credentials", "false")
    if aco:
        assert acc.lower() == "false", (
            f"allow_origins=['*'] must not pair with credentials=true; got ACC={acc}"
        )


def main() -> None:
    client = httpx.Client(timeout=30)
    tests = [
        test_logout_invalidates_token,
        test_other_token_still_valid_after_logout,
        test_search_percent_is_literal,
        test_search_underscore_is_literal,
        test_cors_star_forces_no_credentials,
    ]
    failures = 0
    for t in tests:
        name = t.__name__
        try:
            t(client)
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
