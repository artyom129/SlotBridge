from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.intervals import Interval, generate_slots, merge_intervals, subtract_intervals


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 21, hour, minute, tzinfo=timezone.utc)


def pairs(intervals: list[Interval]) -> list[tuple[datetime, datetime]]:
    return [(item.start, item.end) for item in intervals]


def test_merge_intervals_combines_overlaps_and_adjacent_windows():
    merged = merge_intervals(
        [
            Interval(at(11), at(12)),
            Interval(at(9), at(10)),
            Interval(at(9, 30), at(11)),
            Interval(at(13), at(14)),
        ]
    )

    assert pairs(merged) == [(at(9), at(12)), (at(13), at(14))]


def test_subtract_intervals_merges_and_clips_exclusions():
    remaining = subtract_intervals(
        [Interval(at(9), at(13))],
        [
            Interval(at(8), at(9, 30)),
            Interval(at(10), at(11)),
            Interval(at(10, 30), at(12)),
            Interval(at(12, 30), at(14)),
        ],
    )

    assert pairs(remaining) == [(at(9, 30), at(10)), (at(12), at(12, 30))]


def test_generate_slots_requires_the_full_service_duration():
    work = [Interval(at(9), at(12))]
    slots = generate_slots(work, work, timedelta(minutes=60), timedelta(minutes=15))

    assert [item.start for item in slots] == [
        at(9),
        at(9, 15),
        at(9, 30),
        at(9, 45),
        at(10),
        at(10, 15),
        at(10, 30),
        at(10, 45),
        at(11),
    ]
    assert slots[-1].end == at(12)
