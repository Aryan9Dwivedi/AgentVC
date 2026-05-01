from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for parser in [
        lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")),
        parsedate_to_datetime,
    ]:
        try:
            parsed = parser(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError, IndexError):
            continue
    return None

