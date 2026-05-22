from core.schema import TriageResult

TELEGRAM_MAX = 4000  # leave headroom below the 4096 hard limit


def format_high_priority(result: TriageResult) -> str:
    return (
        "🚨 HIGH PRIORITY EMAIL\n"
        f"{result.step5_message}\n"
        f"📁 Category: {result.step1_category}\n"
        f"🤖 Classified by: {result.llm_provider_used or 'UNKNOWN'}"
    )


def chunk_digest(lines: list[str], header: str, max_len: int = TELEGRAM_MAX) -> list[str]:
    chunks: list[str] = []
    current = header
    for i, line in enumerate(lines, start=1):
        entry = f"\n{i}. {line}"
        if len(current) + len(entry) > max_len:
            chunks.append(current)
            current = f"{header} (cont.){entry}"
        else:
            current += entry
    if current:
        chunks.append(current)
    return chunks


def format_digest_header(count: int) -> str:
    return f"📋 Daily Email Digest ({count} items)"
