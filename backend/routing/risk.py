"""Weather risk rules used to score each checkpoint.

Thresholds (lower bound inclusive, so 25 mph is Moderate, 55 mph is No Travel):

    Condition | Low       | Moderate    | High        | Severe      | No Travel
    Wind      | <25 mph   | 25-34       | 35-44       | 45-54       | >=55 mph
    Rain      | <0.10 in/h| 0.10-0.25   | 0.25-0.50   | 0.50-1.00   | >1.00
    Snow      | <0.5 in/h | 0.5-1.0     | 1.0-2.0     | 2.0-3.0     | >3.0

Where two bands share an edge (e.g. rain 0.25) the value goes to the higher
band. The top band is exclusive for rain and snow (">1.00", ">3.0"), so 1.00 in/h
rain and 3.0 in/h snow are Severe.

Load rules (heavier trucks are more exposed to crosswinds):
    wind >=55 mph                    -> No Travel for any load
    wind 45-54 mph and load >30,000 lb -> No Travel
    wind 35-44 mph and load >40,000 lb -> Severe
"""
from __future__ import annotations

from dataclasses import dataclass, field

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = range(5)
LEVEL_NAMES = ("Low", "Moderate", "High", "Severe", "No Travel")


def wind_level(mph: float) -> int:
    if mph < 25:
        return LOW
    if mph < 35:
        return MODERATE
    if mph < 45:
        return HIGH
    if mph < 55:
        return SEVERE
    return NO_TRAVEL


def rain_level(in_per_hr: float) -> int:
    if in_per_hr < 0.10:
        return LOW
    if in_per_hr < 0.25:
        return MODERATE
    if in_per_hr < 0.50:
        return HIGH
    if in_per_hr <= 1.00:
        return SEVERE
    return NO_TRAVEL


def snow_level(in_per_hr: float) -> int:
    if in_per_hr < 0.5:
        return LOW
    if in_per_hr < 1.0:
        return MODERATE
    if in_per_hr < 2.0:
        return HIGH
    if in_per_hr <= 3.0:
        return SEVERE
    return NO_TRAVEL


def loaded_wind_level(mph: float, load_lb: float) -> tuple[int, str | None]:
    """Wind level after applying the load rules. Returns (level, rule_text_if_applied)."""
    base = wind_level(mph)
    if mph >= 55:
        return NO_TRAVEL, None
    if 45 <= mph < 55 and load_lb > 30_000:
        return NO_TRAVEL, "45-54 mph wind with load over 30,000 lb"
    if 35 <= mph < 45 and load_lb > 40_000:
        return max(base, SEVERE), "35-44 mph wind with load over 40,000 lb"
    return base, None


@dataclass
class Assessment:
    level: int | None  # None when weather data is missing
    wind_level: int | None = None
    rain_level: int | None = None
    snow_level: int | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "Unknown" if self.level is None else LEVEL_NAMES[self.level]


def assess(wind_mph: float | None, rain_in: float | None, snow_in: float | None, load_lb: float) -> Assessment:
    if wind_mph is None and rain_in is None and snow_in is None:
        return Assessment(level=None, reasons=["No forecast available for this time"])

    wl, rule = (loaded_wind_level(wind_mph, load_lb) if wind_mph is not None else (None, None))
    rl = rain_level(rain_in) if rain_in is not None else None
    sl = snow_level(snow_in) if snow_in is not None else None
    levels = [x for x in (wl, rl, sl) if x is not None]
    level = max(levels)

    reasons: list[str] = []
    if level > LOW:
        if wl == level:
            reasons.append(f"Wind {wind_mph:.0f} mph" + (f" ({rule})" if rule else ""))
        if rl == level:
            reasons.append(f"Rain {rain_in:.2f} in/h")
        if sl == level:
            reasons.append(f"Snow {snow_in:.2f} in/h")
    return Assessment(level=level, wind_level=wl, rain_level=rl, snow_level=sl, reasons=reasons)
