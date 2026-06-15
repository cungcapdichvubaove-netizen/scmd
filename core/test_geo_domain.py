# -*- coding: utf-8 -*-

from django.test import SimpleTestCase

from core.domain.geo import GeofenceEvaluator, validate_geofence


class GeofenceEvaluatorTest(SimpleTestCase):
    def test_validate_returns_true_inside_radius_without_db(self):
        result = GeofenceEvaluator.validate(
            user_lat=10.762622,
            user_lng=106.660172,
            target_lat=10.762623,
            target_lng=106.660173,
            radius_m=50,
        )

        self.assertTrue(result.is_within_radius)
        self.assertLess(result.distance_meters, 50)

    def test_validate_wrapper_preserves_backward_compatible_tuple(self):
        is_valid, distance = validate_geofence(
            user_lat=10.762622,
            user_lng=106.660172,
            target_lat=11.0,
            target_lng=107.0,
            radius_m=10,
        )

        self.assertFalse(is_valid)
        self.assertGreater(distance, 10)
