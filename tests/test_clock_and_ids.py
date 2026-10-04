from osahi.clock import FrozenClock
from osahi.ids import SequentialIds


def test_frozen_clock_does_not_move_until_advanced():
    clock = FrozenClock("2026-10-04T04:30:00Z")
    assert clock.now() == "2026-10-04T04:30:00Z"
    assert clock.now() == "2026-10-04T04:30:00Z"
    clock.advance()
    assert clock.now() == "2026-10-04T04:30:01Z"


def test_identifiers_are_ordered_and_kind_prefixed():
    ids = SequentialIds()
    assert ids.next("run") == "run_0001"
    assert ids.next("evt") == "evt_0002"
    assert ids.next("evt") == "evt_0003"
