"""API-equivalent token estimates using a dated standard-price snapshot, not bills."""
from collections import Counter
from decimal import Decimal

AS_OF = '2026-10-31'
SOURCES = {
    'anthropic': 'https://platform.claude.com/docs/en/about-claude/pricing',
    'openai': 'https://developers.openai.com/api/docs/pricing',
    'google': 'https://ai.google.dev/gemini-api/docs/pricing',
}
# USD / million: input, output, cache read, short write, long write.
# Exact model IDs only; provider never determines model pricing.
RATES = {
    'claude-fable-5-1': (10, 50, .25, 12.5, 20),
    'claude-opus-5-5': (4, 20, .20, 5, 8),
    'claude-sonnet-5-5': (2, 10, .10, 2.5, 4),
    'claude-opus-5': (5, 25, .5, 6.25, 10),
    'gpt-6-astra': (10, 50, 1, 12.5, 25),
    'gpt-6.1-sol': (2, 10, .1, 2.5, 5),
    'gpt-6.1-terra': (1, 5, .05, 1.25, 2.5),
    'gpt-6-luna': (.1, .5, .01, .125, .25),
    'gpt-5.6-sol': (4, 20, .4, 5, 10),
    # Promotional snapshot through 2026-11-30; no historical repricing implied.
    'gemini-4-argon': (2, 10, .1, None, None),
}


def estimate(event):
    rate = RATES.get(event.get('model'))
    if rate is None:
        return None, 'unknown_model'
    usage = event.get('usage', {})
    values = [usage.get(k) for k in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens')]
    if any(type(v) is not int or v < 0 for v in values):
        return None, 'missing_usage'
    inp, out, read, write = values
    semantics = event.get('cache_semantics')
    if semantics == 'included':
        inp -= read + write
    elif semantics != 'excluded':
        return None, 'unknown_cache'
    if inp < 0:
        return None, 'invalid_cache'
    if write and (rate[3] is None or rate[4] is None):
        return None, 'unknown_write_rate'
    d = lambda v: Decimal(str(v))
    base = d(inp)*d(rate[0]) + d(out)*d(rate[1]) + d(read)*d(rate[2])
    return tuple((base+d(write)*d(r or 0))/1_000_000 for r in rate[3:]), None


def costs(events):
    low = high = Decimal(0)
    included = 0
    reasons = Counter()
    for event in events:
        if event['event_type'] != 'usage':
            continue
        value, reason = estimate(event)
        if value is None:
            reasons[reason] += 1
        else:
            included += 1
            low += value[0]
            high += value[1]
    missing = sum(reasons.values())
    return dict(estimated_api_equivalent=float(low) if included else None,
                upper_usd=float(high) if included else None,
                currency='USD', quality='estimated' if included else 'unavailable',
                status=('partial' if missing else 'estimated') if included else 'unavailable',
                included_count=included, missing_count=missing, reasons=dict(reasons),
                actual_api_cost=None, subscription_cost=None, price_as_of=AS_OF)
