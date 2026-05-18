from knowledge_base.store.trace_store import TraceStore


async def compute_metrics(store: TraceStore) -> dict:
    all_failures = await store.query_failures()
    slow = await store.query_slow(2000)

    tier_counts: dict[int, int] = {}
    for f in all_failures:
        tier_counts[f.tier] = tier_counts.get(f.tier, 0) + 1

    return {
        "total_failures": len(all_failures),
        "slow_operations_over_2s": len(slow),
        "failures_by_tier": tier_counts,
        "failure_types": _count_by(all_failures, "failure_type"),
    }


def _count_by(events: list, field: str) -> dict:
    counts: dict[str, int] = {}
    for e in events:
        val = getattr(e, field, None) or "unknown"
        counts[val] = counts.get(val, 0) + 1
    return counts
