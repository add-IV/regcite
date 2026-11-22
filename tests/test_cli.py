import uvicorn

from regcite.cli import main


def test_serve_passes_trusted_proxy_and_disables_access_log(monkeypatch):
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))

    assert main(["serve", "--forwarded-allow-ips", "172.17.0.1"]) == 0

    assert calls[0]["forwarded_allow_ips"] == "172.17.0.1"
    assert calls[0]["access_log"] is False
    assert calls[0]["host"] == "127.0.0.1"
