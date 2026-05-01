from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from urllib.error import URLError
from xml.etree import ElementTree


DEFAULT_USER_AGENT = "AgentVC-Generator/0.1"


def fetch_json(url: str, params: dict[str, str | int] | None = None) -> dict:
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            retry_after = int(error.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable json fetch retry state")


def fetch_text(url: str, params: dict[str, str | int] | None = None) -> str:
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", "ignore")
        except HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            retry_after = int(error.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable text fetch retry state")


def fetch_xml(url: str, params: dict[str, str | int] | None = None) -> ElementTree.Element:
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return ElementTree.fromstring(response.read())
        except HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            retry_after = int(error.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable xml fetch retry state")
