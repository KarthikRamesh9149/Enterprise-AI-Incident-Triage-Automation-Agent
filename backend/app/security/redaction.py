import re

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)=([A-Za-z0-9_\-./+=]{6,})"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-./+=]{10,}"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]

INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all )?(previous|prior) instructions"),
    re.compile(r"(?i)reveal (the )?(system prompt|hidden prompt|secrets?)"),
    re.compile(r"(?i)exfiltrate|disable (logging|audit|security)|bypass approval"),
    re.compile(r"(?i)you are now|developer mode|act as root"),
]


def redact_sensitive_text(value: str) -> tuple[str, int]:
    redacted = value
    count = 0
    for pattern in SECRET_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED]", redacted)
        count += replacements
    return redacted, count


def detect_prompt_injection(content: str) -> list[str]:
    return [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(content)]
