"""SaaS 请求进入 LLM、记忆和 Trace 前的轻量脱敏。"""

import re


def redact_sensitive_text(value: str) -> str:
    text = str(value or "")
    # 完整回调 URL 不进入 Prompt；仅保留可用于诊断和白名单的 host。
    text = re.sub(
        r"(?i)\b(webhook|callback|回调)(\s*(?:url|地址)?\s*[:=]?\s*)"
        r"(https?)://([A-Za-z0-9.-]+)(?::\d+)?(?:/[^\s,;，；]*)?",
        lambda match: (
            f"{match.group(1)}{match.group(2)}"
            f"{match.group(3)}://{match.group(4)}/<redacted-path>"
        ),
        text,
    )
    patterns = [
        (r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer <redacted>"),
        (r"(?i)\b(api[_ -]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>"),
        (r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b", "<redacted-secret>"),
        (r"(https?://[^\s?]+)\?[^\s]+", r"\1?<redacted-query>"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text
