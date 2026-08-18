"""weave-note 核心 API 回归测试（wave-2026-08-18 重建）。

运行前提：weave-note 服务已在 127.0.0.1:8201 运行（scripts/start.sh）。
覆盖：auth 全流程 / notebook CRUD / note CRUD / 搜索 / 移动 / 默认笔记本 /
批量操作 / 导出任务 / 文件与图片上传端点存在性。所有用例从 README API 表导出。
"""
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8201"
USER = "test"
PASSWORD = "123456"
PASSED = 0
FAILED = 0


def check(name: str, fn) -> None:
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"PASS {name}")
    except AssertionError as exc:
        FAILED += 1
        print(f"FAIL {name}: {exc}")
    except Exception as exc:
        FAILED += 1
        print(f"ERROR {name}: {type(exc).__name__}: {exc}")


def main():
    client = httpx.Client(timeout=30, base_url=BASE)
    tok = client.post("/api/auth/login", json={"username": USER, "password": PASSWORD})
    assert tok.status_code == 200, f"login: {tok.status_code} {tok.text}"
    token = tok.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    tag = uuid.uuid4().hex[:8]

    def t_auth_flow():
        uname = f"reg_{tag}"
        r = client.post("/api/auth/register", json={"username": uname, "password": "secret123"})
        assert r.status_code == 201, f"register: {r.status_code} {r.text}"
        r2 = client.post("/api/auth/register", json={"username": uname, "password": "secret123"})
        assert r2.status_code == 409, f"dup register: {r2.status_code}"
        r3 = client.post("/api/auth/login", json={"username": uname, "password": "wrong"})
        assert r3.status_code == 401, f"bad login: {r3.status_code}"
        r4 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r4.status_code == 200

    def t_notebook_crud():
        r = client.post("/api/notes/notebooks", headers=H, json={"name": f"nb_{tag}"})
        assert r.status_code in (200, 201), f"create nb: {r.status_code} {r.text}"
        nb = r.json()
        nb_id = nb["id"]
        r2 = client.get("/api/notes/notebooks", headers=H)
        assert r2.status_code == 200 and any(n["id"] == nb_id for n in r2.json())
        r3 = client.put(f"/api/notes/notebooks/{nb_id}", headers=H, json={"name": f"nb_{tag}_renamed"})
        assert r3.status_code == 200 and r3.json()["name"] == f"nb_{tag}_renamed"
        r4 = client.delete(f"/api/notes/notebooks/{nb_id}", headers=H)
        assert r4.status_code == 200

    def t_note_crud():
        nb_id = client.get("/api/notes/default-notebook", headers=H).json()["id"]
        r = client.post(f"/api/notes/notebooks/{nb_id}/notes", headers=H,
                        json={"title": f"note_{tag}", "content": f"content {tag}"})
        assert r.status_code in (200, 201), f"create note: {r.status_code} {r.text}"
        note = r.json()
        nid = note["id"]
        r2 = client.get(f"/api/notes/notes/{nid}", headers=H)
        assert r2.status_code == 200 and r2.json()["title"] == f"note_{tag}"
        r3 = client.put(f"/api/notes/notes/{nid}", headers=H,
                        json={"title": f"note_{tag}_2", "content": "updated"})
        assert r3.status_code == 200 and r3.json()["title"] == f"note_{tag}_2"
        r4 = client.post("/api/notes/quick", headers=H, json={"transcription": f"quick {tag}"})
        assert r4.status_code in (200, 201), f"quick: {r4.status_code} {r4.text}"
        r5 = client.delete(f"/api/notes/notes/{nid}", headers=H)
        assert r5.status_code == 200

    def t_search():
        nb_id = client.get("/api/notes/default-notebook", headers=H).json()["id"]
        client.post(f"/api/notes/notebooks/{nb_id}/notes", headers=H,
                    json={"title": f"搜索目标{tag}", "content": "独特关键词xyz"})
        r = client.get("/api/notes/search", headers=H, params={"q": "独特关键词xyz"})
        assert r.status_code == 200 and r.json(), f"search miss: {r.text}"

    def t_move_and_bulk():
        nb1 = client.post("/api/notes/notebooks", headers=H, json={"name": f"mv1_{tag}"}).json()["id"]
        nb2 = client.post("/api/notes/notebooks", headers=H, json={"name": f"mv2_{tag}"}).json()["id"]
        nid = client.post(f"/api/notes/notebooks/{nb1}/notes", headers=H,
                          json={"title": f"mv_{tag}", "content": "x"}).json()["id"]
        r = client.put(f"/api/notes/notes/{nid}/move", headers=H, json={"target_notebook_id": nb2})
        assert r.status_code == 200, f"move: {r.status_code} {r.text}"
        r2 = client.get(f"/api/notes/notes/{nid}", headers=H)
        assert r2.json()["notebook_id"] == nb2
        r3 = client.post("/api/notes/notes/bulk-delete", headers=H, json={"note_ids": [nid]})
        assert r3.status_code == 200
        client.delete(f"/api/notes/notebooks/{nb1}", headers=H)
        client.delete(f"/api/notes/notebooks/{nb2}", headers=H)

    def t_default_notebook():
        r = client.get("/api/notes/default-notebook", headers=H)
        assert r.status_code == 200 and r.json().get("is_default") is True

    def t_export_task():
        nb_id = client.get("/api/notes/default-notebook", headers=H).json()["id"]
        r = client.post("/api/export-tasks", headers=H,
                        json={"task_type": "single", "format": "md",
                              "note_id": client.post(f"/api/notes/notebooks/{nb_id}/notes",
                                                     headers=H, json={"title": f"exp_{tag}", "content": "c"}).json()["id"]})
        assert r.status_code in (200, 201), f"export task: {r.status_code} {r.text}"
        tid = r.json()["id"]
        r2 = client.get(f"/api/export-tasks/{tid}", headers=H)
        assert r2.status_code == 200 and r2.json()["id"] == tid
        r3 = client.get("/api/export-tasks", headers=H)
        assert r3.status_code == 200

    def t_upload_endpoints():
        # files/upload 是 multipart 上传（缺文件时 422 校验失败属预期契约）
        r = client.post("/api/files/upload", headers=H)
        assert r.status_code in (400, 413, 422, 200), f"files/upload: {r.status_code}"
        r2 = client.post("/api/images/upload", headers=H)
        assert r2.status_code in (400, 413, 422, 200), f"images/upload: {r2.status_code}"
        r3 = client.get("/api/images/serve", headers=H, params={"path": "nonexistent.png"})
        assert r3.status_code in (401, 400, 404), f"images/serve: {r3.status_code}"

    check("auth_flow", t_auth_flow)
    check("notebook_crud", t_notebook_crud)
    check("note_crud", t_note_crud)
    check("search", t_search)
    check("move_and_bulk", t_move_and_bulk)
    check("default_notebook", t_default_notebook)
    check("export_task", t_export_task)
    check("upload_endpoints", t_upload_endpoints)

    print(f"\n{PASSED}/{PASSED + FAILED} passed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
