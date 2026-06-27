"""Shared HTTP proxy resolution and enforcement for CLI API calls."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any

import requests

_PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
)

_REGION_ERROR_HINT = (
    "若已配置代理仍出现地区限制，可能是 Clash 规则模式下 openrouter.ai 走了直连。"
    "请在 Clash 规则中将 DOMAIN-SUFFIX,openrouter.ai 设为 PROXY，或临时切换全局模式。"
)


def region_error_hint() -> str:
    return _REGION_ERROR_HINT


def read_macos_system_proxy() -> str | None:
    """Read HTTP proxy from macOS system settings (Clash sets these)."""
    if sys.platform != "darwin":
        return None
    try:
        output = subprocess.check_output(
            ["scutil", "--proxy"], text=True, timeout=5, stderr=subprocess.DEVNULL
        )
    except (subprocess.SubprocessError, OSError):
        return None

    if re.search(r"HTTPEnable\s*:\s*1", output):
        host = re.search(r"HTTPProxy\s*:\s*(\S+)", output)
        port = re.search(r"HTTPPort\s*:\s*(\d+)", output)
        if host and port:
            return f"http://{host.group(1)}:{port.group(1)}"

    if re.search(r"HTTPSEnable\s*:\s*1", output):
        host = re.search(r"HTTPSProxy\s*:\s*(\S+)", output)
        port = re.search(r"HTTPSPort\s*:\s*(\d+)", output)
        if host and port:
            return f"http://{host.group(1)}:{port.group(1)}"

    return None


def config_proxy_value(config: dict[str, Any]) -> str | None:
    """Pick proxy from config top-level or image/prompt/video sections."""
    if isinstance(config.get("proxy"), str) and config["proxy"].strip():
        return config["proxy"].strip()
    for section in ("host", "image", "prompt", "code", "video"):
        block = config.get(section)
        if isinstance(block, dict):
            value = block.get("proxy")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def resolve_proxy(
    cli_value: str | None = None,
    config_value: str | None = None,
) -> str | None:
    """Resolve proxy: CLI > config > env vars > macOS system proxy."""
    if cli_value:
        return cli_value.strip()
    if config_value:
        return str(config_value).strip()
    for key in ("GAMEFACTORY_PROXY", *_PROXY_ENV_KEYS):
        value = os.environ.get(key)
        if value:
            return value.strip()
    return read_macos_system_proxy()


def resolve_config_proxy(
    config: dict[str, Any],
    cli_value: str | None = None,
) -> str | None:
    """Resolve proxy for any CLI command from config + environment."""
    return resolve_proxy(cli_value, config_proxy_value(config))


def apply_proxy_env(proxy: str | None) -> str | None:
    """Inject proxy into process env so requests/subprocesses use it consistently."""
    if not proxy:
        return None
    for key in _PROXY_ENV_KEYS:
        os.environ[key] = proxy
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")
    os.environ.setdefault("NO_PROXY", os.environ["no_proxy"])
    return proxy


def proxy_dict(proxy: str | None) -> dict[str, str] | None:
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def create_http_session(proxy: str | None) -> requests.Session:
    """Session that always routes through proxy when one is configured."""
    session = requests.Session()
    if proxy:
        session.trust_env = False
        session.proxies.update(proxy_dict(proxy) or {})
    return session


def http_get(proxy: str | None, url: str, **kwargs: Any) -> requests.Response:
    return create_http_session(proxy).get(url, **kwargs)


def http_post(proxy: str | None, url: str, **kwargs: Any) -> requests.Response:
    return create_http_session(proxy).post(url, **kwargs)


def activate_proxy(config: dict[str, Any], cli_value: str | None = None) -> str | None:
    """Resolve proxy from all sources and apply to the current process."""
    proxy = resolve_config_proxy(config, cli_value)
    return apply_proxy_env(proxy)
