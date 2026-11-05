import json
from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase, override_settings

from routing import geo
from routing.hos import HOSRules, build_timeline
from routing.planner import _checkpoint_marks, explain, rank_key
from routing.providers.openmeteo import parse_location
from routing.providers.osrm import parse_route
from routing.risk import HIGH, LOW, MODERATE, NO_TRAVEL, SEVERE, assess, rain_level, snow_level, wind_level


class RiskRulesTests(SimpleTestCase):
    def test_wind_bands_lower_bound_inclusive(self):
        cases = [(0, LOW), (24.9, LOW), (25, MODERATE), (34.9, MODERATE), (35, HIGH), (44.9, HIGH),
                 (45, SEVERE), (54.9, SEVERE), (55, NO_TRAVEL), (80, NO_TRAVEL)]
        for mph, expected in cases:
            self.assertEqual(wind_level(mph), expected, mph)

    def test_rain_bands(self):
        cases = [(0, LOW), (0.099, LOW), (0.10, MODERATE), (0.25, HIGH), (0.5, SEVERE), (1.0, SEVERE), (1.01, NO_TRAVEL)]
        for v, expected in cases:
            self.assertEqual(rain_level(v), expected, v)

    def test_snow_bands(self):
        cases = [(0.49, LOW), (0.5, MODERATE), (1.0, HIGH), (2.0, SEVERE), (3.0, SEVERE), (3.1, NO_TRAVEL)]
        for v, expected in cases:
            self.assertEqual(snow_level(v), expected, v)

    def test_load_rules(self):
        # >=55 mph is No Travel for any load
        self.assertEqual(assess(56, 0, 0, 0).level, NO_TRAVEL)
        # 45-54 mph: Severe when light, No Travel above 30,000 lb
        self.assertEqual(assess(50, 0, 0, 30_000).level, SEVERE)
        self.assertEqual(assess(50, 0, 0, 30_001).level, NO_TRAVEL)
        # 35-44 mph: High when <=40,000 lb, Severe above
        self.assertEqual(assess(40, 0, 0, 40_000).level, HIGH)
        self.assertEqual(assess(40, 0, 0, 40_001).level, SEVERE)
        # Load never lowers risk and doesn't affect calm wind
        self.assertEqual(assess(20, 0, 0, 80_000).level, LOW)

    def test_worst_condition_wins_and_is_explained(self):
        a = assess(30, 0.6, 0.0, 10_000)
        self.assertEqual(a.level, SEVERE)
        self.assertEqual(a.reasons, ["Rain 0.60 in/h"])

    def test_missing_data_is_unknown(self):
        a = assess(None, None, None, 10_000)
        self.assertIsNone(a.level)
        self.assertEqual(a.name, "Unknown")


class HOSTests(SimpleTestCase):
    def test_breaks_and_reset(self):
        # 12 one-hour segments of 60 miles.
        seg_t, seg_d = [3600.0] * 12, [96_560.6] * 12
        elapsed, stops = build_timeline(seg_d, seg_t, HOSRules())
        self.assertEqual([s.kind for s in stops], ["break", "reset"])
        self.assertAlmostEqual(stops[0].start_offset_s, 8 * 3600)
        self.assertAlmostEqual(stops[1].start_offset_s, 11.5 * 3600)  # 11 h driving + 30 min break
        # 12 h driving + 0.5 h break + 10 h reset
        self.assertAlmostEqual(elapsed[-1], 22.5 * 3600)

    def test_no_rules_means_plain_driving_time(self):
        elapsed, stops = build_timeline([1000.0] * 3, [60.0] * 3, None)
        self.assertEqual(stops, [])
        self.assertEqual(elapsed, [0.0, 60.0, 120.0, 180.0])

    def test_break_splits_segment_at_correct_distance(self):
        # One 10-hour segment of 1,000 km: break after 8 h -> at 800 km.
        _, stops = build_timeline([1_000_000.0], [36_000.0], HOSRules())
        self.assertAlmostEqual(stops[0].at_m, 800_000.0)


class GeoAndCheckpointTests(SimpleTestCase):
    def test_checkpoints_every_interval_plus_destination(self):
        total = 60 * geo.METERS_PER_MILE
        marks = _checkpoint_marks(total, 25)
        self.assertEqual([round(m / geo.METERS_PER_MILE) for m in marks], [0, 25, 50, 60])

    def test_exact_multiple_has_no_duplicate_end(self):
        marks = _checkpoint_marks(50 * geo.METERS_PER_MILE, 25)
        self.assertEqual(len(marks), 3)

    def test_interpolate_midpoint(self):
        coords = [(0.0, 0.0), (0.0, 1.0)]
        cum = geo.cumulative_distances(coords)
        (lat, lon), _ = geo.interpolate(coords, cum, cum[-1] / 2)
        self.assertAlmostEqual(lon, 0.5)

    def test_mercator_round_trip(self):
        for lat in (-60, 0, 33.3, 47.9):
            self.assertAlmostEqual(geo.inverse_mercator_y(geo.mercator_y(lat)), lat)


class RankingTests(SimpleTestCase):
    def route(self, name, miles, avg, hours):
        return {"name": name, "miles_by_level": miles, "avg_risk": avg, "total_hours": hours}

    def test_order_follows_brief(self):
        fast_but_severe = self.route("A", [500, 0, 0, 20, 0], 0.4, 10)
        slow_safe = self.route("B", [500, 50, 30, 0, 0], 0.5, 14)
        self.assertEqual(min([fast_but_severe, slow_safe], key=rank_key)["name"], "B")

    def test_no_travel_ranks_last(self):
        nt = self.route("A", [500, 0, 0, 0, 5], 0.1, 10)
        severe = self.route("B", [500, 0, 0, 200, 0], 1.5, 12)
        self.assertEqual(min([nt, severe], key=rank_key)["name"], "B")

    def test_time_breaks_full_tie_and_reason_says_so(self):
        a = self.route("A", [500, 10, 0, 0, 0], 0.2, 10)
        b = self.route("B", [500, 10, 0, 0, 0], 0.2, 11)
        best = min([a, b], key=rank_key)
        self.assertEqual(best["name"], "A")
        self.assertIn("fastest", explain(best, [b]))


class ProviderParsingTests(SimpleTestCase):
    def test_osrm_multi_leg_annotations(self):
        route = {
            "distance": 3000, "duration": 300,
            "geometry": {"coordinates": [[0, 0], [0.01, 0], [0.02, 0], [0.03, 0]]},
            "legs": [{"annotation": {"duration": [100, 100]}}, {"annotation": {"duration": [100]}}],
        }
        r = parse_route(route)
        self.assertEqual(r.seg_dur_s, [100.0, 100.0, 100.0])
        self.assertEqual(len(r.seg_dist_m), 3)

    def test_osrm_mismatched_annotations_fall_back_to_distance_share(self):
        route = {"distance": 2000, "duration": 200,
                 "geometry": {"coordinates": [[0, 0], [0.01, 0], [0.03, 0]]},
                 "legs": [{"annotation": {"duration": [1]}}]}
        r = parse_route(route)
        self.assertAlmostEqual(sum(r.seg_dur_s), 200)
        self.assertAlmostEqual(r.seg_dur_s[1], 2 * r.seg_dur_s[0], places=3)

    def test_open_meteo_series_lookup(self):
        loc = {"hourly": {"time": ["2026-11-05T00:00", "2026-11-05T01:00"],
                          "wind_speed_10m": [10, 40], "wind_gusts_10m": [15, 60], "rain": [0, 0.3], "snowfall": [0, 0]}}
        s = parse_location(loc)
        when = datetime(2026, 11, 5, 0, 40, tzinfo=timezone.utc)  # rounds to 01:00
        self.assertEqual(s.at(when), (40.0, 60.0, 0.3, 0.0))
        self.assertEqual(s.at(when + timedelta(hours=5)), (None, None, None, None))


@override_settings(MOCK_PROVIDERS=True)
class ApiTests(SimpleTestCase):
    def payload(self, **kw):
        body = {"origin": "Chicago", "destination": "Denver",
                "departure": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "load_lb": 35_000, "interval_mi": 25, "hos": True}
        body.update(kw)
        return json.dumps(body)

    def test_plan_and_heatmap(self):
        r = self.client.post("/api/plan", self.payload(), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["routes"]), 3)
        self.assertEqual(sum(rt["recommended"] for rt in data["routes"]), 1)
        rec = next(rt for rt in data["routes"] if rt["recommended"])
        self.assertEqual(rec["id"], data["recommendation"]["route_id"])
        self.assertEqual(rec, min(data["routes"], key=rank_key))
        for rt in data["routes"]:
            miles = [c["mile"] for c in rt["checkpoints"]]
            self.assertEqual(miles, sorted(miles))
            self.assertAlmostEqual(sum(rt["miles_by_level"]) + rt["unknown_miles"], rt["distance_mi"], delta=0.5)
            etas = [c["eta"] for c in rt["checkpoints"]]
            self.assertEqual(etas, sorted(etas))

        h = self.client.get(f"/api/plan/{data['plan_id']}/heatmap")
        self.assertEqual(h.status_code, 200)
        hm = h.json()
        self.assertEqual(len(hm["times"]), 49)
        self.assertEqual(len(hm["cells"]), len(hm["wind_mph"]))
        self.assertTrue(all(0 <= c < hm["nx"] * hm["ny"] for c in hm["cells"]))

    def test_validation_errors(self):
        for kw, msg in [({"interval_mi": 15}, "interval"), ({"load_lb": -5}, "Load"),
                        ({"departure": "2020-01-01T00:00:00Z"}, "past"), ({"destination": "Atlantis"}, "find")]:
            r = self.client.post("/api/plan", self.payload(**kw), content_type="application/json")
            self.assertEqual(r.status_code, 400, kw)
            self.assertIn(msg, r.json()["error"])

    def test_expired_plan_heatmap_is_404(self):
        self.assertEqual(self.client.get("/api/plan/nope/heatmap").status_code, 404)
