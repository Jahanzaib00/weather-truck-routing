"""Turns driving time into real elapsed time, inserting Hours-of-Service rest.

Simplified FMCSA property-carrying rules:
  * a 30-minute break after 8 cumulative hours of driving
  * a 10-hour off-duty reset after 11 hours of driving

The 14-hour on-duty window and the 70-hour/8-day limit are not modelled; for a
single trip driven continuously these two rules decide when the truck stops.

This matters for weather: on a 1,000-mile run the truck reaches the far end
many hours later than a car-style ETA, so it meets a different forecast hour.
"""
from __future__ import annotations

from dataclasses import dataclass

HOUR = 3600.0


@dataclass(frozen=True)
class HOSRules:
    drive_before_break_s: float = 8 * HOUR
    break_s: float = 0.5 * HOUR
    drive_before_reset_s: float = 11 * HOUR
    reset_s: float = 10 * HOUR


@dataclass
class RestStop:
    kind: str  # "break" | "reset"
    at_m: float  # distance along the route
    start_offset_s: float  # seconds after departure
    duration_s: float


def build_timeline(
    seg_dist_m: list[float], seg_dur_s: list[float], rules: HOSRules | None
) -> tuple[list[float], list[RestStop]]:
    """Elapsed seconds at every vertex, plus the rest stops taken.

    `seg_dist_m[i]` / `seg_dur_s[i]` describe the segment from vertex i to i+1.
    """
    elapsed = [0.0]
    stops: list[RestStop] = []
    clock = 0.0
    dist = 0.0
    since_break = 0.0
    since_reset = 0.0

    for seg_d, seg_t in zip(seg_dist_m, seg_dur_s):
        remaining_t, remaining_d = seg_t, seg_d
        while rules is not None and remaining_t > 0:
            until_break = rules.drive_before_break_s - since_break
            until_reset = rules.drive_before_reset_s - since_reset
            limit = min(until_break, until_reset)
            if remaining_t <= limit:
                break
            # Drive up to the limit, then stop in the middle of this segment.
            frac = limit / remaining_t
            clock += limit
            dist += remaining_d * frac
            remaining_d -= remaining_d * frac
            remaining_t -= limit
            since_break += limit
            since_reset += limit
            if since_reset >= rules.drive_before_reset_s - 1e-6:
                stops.append(RestStop("reset", dist, clock, rules.reset_s))
                clock += rules.reset_s
                since_break = since_reset = 0.0
            else:
                stops.append(RestStop("break", dist, clock, rules.break_s))
                clock += rules.break_s
                since_break = 0.0
        clock += remaining_t
        dist += remaining_d
        since_break += remaining_t
        since_reset += remaining_t
        elapsed.append(clock)
    return elapsed, stops
