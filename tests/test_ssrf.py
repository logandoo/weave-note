"""SSRF 防护单测：file_upload._assert_safe_download_url。

运行：weave-note/.venv/bin/python tests/test_ssrf.py（无需服务在线）。
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.api.file_upload import _assert_safe_download_url

PASSED = 0
FAILED = 0


def check(name: str, fn):
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


def t_public_https_allowed():
    with patch("app.api.file_upload.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
        _assert_safe_download_url("https://example.com/img.png")  # 不应抛错


def t_loopback_blocked():
    with patch("app.api.file_upload.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))]):
        try:
            _assert_safe_download_url("http://127.0.0.1:8201/img.png")
        except ValueError:
            return
        raise AssertionError("127.0.0.1 应被拒绝")


def t_metadata_ip_blocked():
    with patch("app.api.file_upload.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("169.254.169.254", 0))]):
        try:
            _assert_safe_download_url("http://169.254.169.254/latest/meta-data/")
        except ValueError:
            return
        raise AssertionError("云元数据地址应被拒绝")


def t_private_blocked():
    with patch("app.api.file_upload.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.5", 0))]):
        try:
            _assert_safe_download_url("http://10.0.0.5/admin")
        except ValueError:
            return
        raise AssertionError("内网 10.x 应被拒绝")


def t_scheme_rejected():
    try:
        _assert_safe_download_url("file:///etc/passwd")
    except ValueError:
        return
    raise AssertionError("非 http(s) scheme 应被拒绝")


def t_mixed_dns_blocks_private():
    # 多 A 记录：任一解析为内网即拒绝
    with patch("app.api.file_upload.socket.getaddrinfo", return_value=[
        (2, 1, 6, "", ("93.184.216.34", 0)),
        (2, 1, 6, "", ("192.168.1.10", 0)),
    ]):
        try:
            _assert_safe_download_url("https://dual.example.com/img.png")
        except ValueError:
            return
        raise AssertionError("任一记录指向内网应被拒绝")


def main():
    check("public_https_allowed", t_public_https_allowed)
    check("loopback_blocked", t_loopback_blocked)
    check("metadata_ip_blocked", t_metadata_ip_blocked)
    check("private_blocked", t_private_blocked)
    check("scheme_rejected", t_scheme_rejected)
    check("mixed_dns_blocks_private", t_mixed_dns_blocks_private)
    print(f"\n{PASSED}/{PASSED + FAILED} passed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
