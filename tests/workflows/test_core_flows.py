"""weave-note 工作流场景测试（§A4.7b）：跨端点的业务任务级验证。

场景 1（happy path）：登录 → 建笔记本 → 建笔记 → 搜索命中 → 移动 → 确认落位
场景 2（登出安全）：登录 → 登出 → 同 token 访问受保护端点 → 401
场景 3（越权拒绝）：用户 A 的 token 访问/修改用户 B 的笔记 → 404/403
"""
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8201"
TAG = uuid.uuid4().hex[:8]


def main():
    client = httpx.Client(timeout=30, base_url=BASE)
    failed = []

    # --- 场景 1: 登录→建笔记本→建笔记→搜索→移动→落位验证 ---
    try:
        tok = client.post("/api/auth/login", json={"username": "test", "password": "123456"})
        assert tok.status_code == 200, tok.text
        H = {"Authorization": f"Bearer {tok.json()['access_token']}"}

        nb = client.post("/api/notes/notebooks", headers=H, json={"name": f"wf1_{TAG}"}).json()
        note = client.post(f"/api/notes/notebooks/{nb['id']}/notes", headers=H,
                           json={"title": f"wf1_note_{TAG}", "content": "跨端点状态验证文本"}).json()
        search = client.get("/api/notes/search", headers=H, params={"q": "跨端点状态验证文本"})
        assert search.status_code == 200 and search.json(), f"搜索未命中: {search.text}"
        assert search.json()[0]["note_id"] == note["id"]

        nb2 = client.post("/api/notes/notebooks", headers=H, json={"name": f"wf1b_{TAG}"}).json()
        mv = client.put(f"/api/notes/notes/{note['id']}/move", headers=H,
                        json={"target_notebook_id": nb2["id"]})
        assert mv.status_code == 200, mv.text

        verify = client.get(f"/api/notes/notes/{note['id']}", headers=H)
        assert verify.json()["notebook_id"] == nb2["id"], "移动后落位不一致"
        client.delete(f"/api/notes/notebooks/{nb['id']}", headers=H)
        client.delete(f"/api/notes/notebooks/{nb2['id']}", headers=H)
        print("PASS workflow_1_happy_path")
    except AssertionError as exc:
        failed.append(f"workflow_1_happy_path: {exc}")
        print(f"FAIL workflow_1_happy_path: {exc}")

    # --- 场景 2: 登出后 token 立即失效 ---
    try:
        tok = client.post("/api/auth/login", json={"username": "test", "password": "123456"})
        H = {"Authorization": f"Bearer {tok.json()['access_token']}"}
        assert client.get("/api/auth/me", headers=H).status_code == 200
        client.post("/api/auth/logout", headers=H)
        r = client.get("/api/notes/notebooks", headers=H)
        assert r.status_code == 401, f"登出后应 401, got {r.status_code}"
        print("PASS workflow_2_logout_revokes")
    except AssertionError as exc:
        failed.append(f"workflow_2_logout_revokes: {exc}")
        print(f"FAIL workflow_2_logout_revokes: {exc}")

    # --- 场景 3: 越权拒绝（用户 B 无法访问用户 A 的笔记） ---
    try:
        uname_a, uname_b = f"wf_a_{TAG}", f"wf_b_{TAG}"
        client.post("/api/auth/register", json={"username": uname_a, "password": "secret123"})
        client.post("/api/auth/register", json={"username": uname_b, "password": "secret123"})
        tok_a = client.post("/api/auth/login", json={"username": uname_a, "password": "secret123"}).json()["access_token"]
        tok_b = client.post("/api/auth/login", json={"username": uname_b, "password": "secret123"}).json()["access_token"]
        HA, HB = {"Authorization": f"Bearer {tok_a}"}, {"Authorization": f"Bearer {tok_b}"}

        nb_a = client.post("/api/notes/notebooks", headers=HA, json={"name": f"wf3_{TAG}"}).json()
        note_a = client.post(f"/api/notes/notebooks/{nb_a['id']}/notes", headers=HA,
                             json={"title": "A 的私有笔记", "content": "secret"}).json()

        r = client.get(f"/api/notes/notes/{note_a['id']}", headers=HB)
        assert r.status_code == 404, f"B 访问 A 的笔记应 404, got {r.status_code} {r.text}"
        r2 = client.put(f"/api/notes/notes/{note_a['id']}", headers=HB,
                        json={"title": "hacked", "content": "x"})
        assert r2.status_code in (404, 403), f"B 修改 A 的笔记应 404/403, got {r2.status_code}"
        print("PASS workflow_3_cross_user_denied")
    except AssertionError as exc:
        failed.append(f"workflow_3_cross_user_denied: {exc}")
        print(f"FAIL workflow_3_cross_user_denied: {exc}")

    print(f"\n{3 - len(failed)}/3 workflows passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
