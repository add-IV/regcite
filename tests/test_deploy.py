import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_caddy_writes_no_access_log():
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    directives = [line.split("#")[0].strip() for line in caddyfile.splitlines()]

    assert not [d for d in directives if d.split(" ")[:1] == ["log"]]
    assert "reverse_proxy 127.0.0.1:8000" in directives


def test_container_binds_loopback_and_trusts_only_local_proxy():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    cmd = json.loads(re.search(r"^CMD (\[.*\])$", dockerfile, re.M).group(1))

    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"
    assert cmd[cmd.index("--forwarded-allow-ips") + 1] == "127.0.0.1"


def test_page_has_no_inline_script_or_style_for_the_csp():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert re.findall(r"<script(?![^>]*\bsrc=)", html) == []
    assert "<style" not in html
    assert " style=" not in html
    assert not re.search(r"\son[a-z]+=", html)


def test_torch_comes_from_the_cpu_index_on_linux():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    (source,) = pyproject["tool"]["uv"]["sources"]["torch"]
    index = {i["name"]: i["url"] for i in pyproject["tool"]["uv"]["index"]}

    assert source["marker"] == "sys_platform == 'linux'"
    assert index[source["index"]].endswith("/whl/cpu")
