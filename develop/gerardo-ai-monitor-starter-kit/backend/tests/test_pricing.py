from copy import deepcopy
import pytest
from monitor.pricing import costs
from monitor.service import demo_events, overview
from monitor.store import Store


def event(model='gpt-6.1-sol', semantics='included'):
    return dict(event_type='usage', model=model, provider='codex', cache_semantics=semantics,
                usage=dict(input_tokens=1_000_000, output_tokens=100_000,
                           cache_read_tokens=400_000, cache_write_tokens=0))


def test_cached_input_is_not_charged_twice():
    row = event()
    row['usage_mode'] = 'cumulative'  # normalized usage is already a delta
    row['raw_usage'] = {'input_tokens': 999_000_000}
    assert costs([row])['estimated_api_equivalent'] == pytest.approx(2.24)
    row['provider'] = 'antigravity'  # price follows model, not tool
    assert costs([row])['estimated_api_equivalent'] == pytest.approx(2.24)


def test_claude_excluded_cache_and_write_midpoint():
    row = event('claude-opus-5-5', 'excluded')
    row['usage']['cache_write_tokens'] = 100_000
    cost = costs([row])
    assert cost['estimated_api_equivalent'] == pytest.approx(6.73)
    assert cost['lower_usd'] == pytest.approx(6.58)
    assert cost['upper_usd'] == pytest.approx(6.88)


def test_partial_unknown_and_empty_are_not_zero():
    known = event()
    unknown = event('unlisted-model')
    missing = deepcopy(known)
    missing['usage']['cache_read_tokens'] = None
    result = costs([known, unknown, missing])
    assert result['status'] == 'partial'
    assert result['included_count'] == 1 and result['missing_count'] == 2
    assert result['estimated_api_equivalent'] == pytest.approx(2.24)
    assert costs([])['estimated_api_equivalent'] is None
    assert costs([unknown])['estimated_api_equivalent'] is None
    for k in known['usage']:
        known['usage'][k] = 0
    assert costs([known])['estimated_api_equivalent'] == 0


def test_invalid_or_unknown_cache_is_excluded():
    row = event(semantics='unknown')
    assert costs([row])['estimated_api_equivalent'] is None
    row['cache_semantics'] = 'included'
    row['usage']['cache_read_tokens'] = 2_000_000
    assert costs([row])['estimated_api_equivalent'] is None


def test_filtered_costs_reconcile(tmp_path):
    store = Store(tmp_path/'test.sqlite3', {})
    events = demo_events()
    data = overview(events, store.sources(), {}, period='all', provider='antigravity')
    amount = data['cost']['estimated_api_equivalent']
    assert amount > 0
    assert amount == pytest.approx(sum(t['cost']['estimated_api_equivalent'] for t in data['tasks']))
    assert amount == pytest.approx(sum(p['cost']['estimated_api_equivalent'] for p in data['projects']))
    assert amount == pytest.approx(sum(p['antigravity']['estimated_api_equivalent'] or 0 for p in data['cost_series']))
    assert data['providers'][0]['cost']['estimated_api_equivalent'] is None
    assert data['providers'][2]['cost']['estimated_api_equivalent'] == amount
