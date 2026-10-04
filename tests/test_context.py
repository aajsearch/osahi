import pytest

from osahi.context import WorkingContext


def test_budget_below_two_is_rejected():
    with pytest.raises(ValueError):
        WorkingContext(1)


def test_crossing_the_budget_keeps_a_summary_and_reports_the_drop_count():
    context = WorkingContext(2)
    assert context.compaction_for({"role": "user", "content": "one"}) is None
    context.add({"role": "user", "content": "one"})
    assert context.compaction_for({"role": "user", "content": "two"}) is None
    context.add({"role": "user", "content": "two"})
    compaction = context.compaction_for({"role": "user", "content": "three"})
    assert compaction == {
        "dropped": 2,
        "retained": [{"role": "summary", "content": "compacted 2 items"}],
    }
    context.add({"role": "user", "content": "three"})
    assert context.items == [
        {"role": "summary", "content": "compacted 2 items"},
        {"role": "user", "content": "three"},
    ]
