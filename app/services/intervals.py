from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, order=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Intervals must use timezone-aware datetimes")
        if self.start >= self.end:
            raise ValueError("Interval start must be before end")


def merge_intervals(intervals: list[Interval]) -> list[Interval]:
    """Merge overlapping and adjacent intervals into a sorted non-overlapping list."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda item: item.start)
    merged: list[Interval] = [ordered[0]]
    for current in ordered[1:]:
        previous = merged[-1]
        if current.start <= previous.end:
            merged[-1] = Interval(previous.start, max(previous.end, current.end))
        else:
            merged.append(current)
    return merged


def subtract_intervals(
    available: list[Interval], exclusions: list[Interval]
) -> list[Interval]:
    """Subtract any overlaps, clipping exclusions that extend beyond work windows."""
    remaining: list[Interval] = []
    merged_exclusions = merge_intervals(exclusions)
    for base in merge_intervals(available):
        cursor = base.start
        for exclusion in merged_exclusions:
            if exclusion.end <= cursor:
                continue
            if exclusion.start >= base.end:
                break
            if exclusion.start > cursor:
                remaining.append(Interval(cursor, min(exclusion.start, base.end)))
            cursor = max(cursor, exclusion.end)
            if cursor >= base.end:
                break
        if cursor < base.end:
            remaining.append(Interval(cursor, base.end))
    return remaining


def generate_slots(
    work_windows: list[Interval],
    free_windows: list[Interval],
    duration: timedelta,
    step: timedelta,
) -> list[Interval]:
    """Generate starts on each work-window grid only when full duration is free."""
    if duration <= timedelta(0) or step <= timedelta(0):
        raise ValueError("Duration and step must be positive")
    slots: list[Interval] = []
    merged_work = merge_intervals(work_windows)
    merged_free = merge_intervals(free_windows)
    for work in merged_work:
        candidate_start = work.start
        while candidate_start + duration <= work.end:
            candidate = Interval(candidate_start, candidate_start + duration)
            if any(
                free.start <= candidate.start and candidate.end <= free.end
                for free in merged_free
            ):
                slots.append(candidate)
            candidate_start += step
    return slots
