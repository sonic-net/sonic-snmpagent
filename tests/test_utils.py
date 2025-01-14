from unittest import TestCase

from ax_interface.util import get_next_update_interval


class TestUtil(TestCase):
    # Given: Update is quick, execution time is 0.000001, static interval is 5/10/15s
    # When: get next interval
    # Then: Return default interval, 5/10/15s
    def test_get_interval_quick_finish(self):
        for static_interval in [5, 10, 15]:
            self.assertEqual(get_next_update_interval(0.000001, static_interval), static_interval)

    # Given: Update is slow, execution time is 0.7666666, static interval is 5
    # When: get next interval
    # Then: Return the ceil(0.766666 * 10) = 8
    def test_get_interval_slow_finish(self):
        self.assertEqual(get_next_update_interval(0.766666, 5), 8)

    # Given: Update is slow, execution time is 0.766666, static interval is 10
    # When: get next interval
    # Then: Return default interval, 10
    def test_get_interval_slow_finish_default_long(self):
        self.assertEqual(get_next_update_interval(0.766666, 10), 10)

    # Given: Update is very slow, execution time is 20.2324, static interval is 10
    # When: get next interval
    # Then: Return max interval, 60
    def test_get_interval_very_slow(self):
        self.assertEqual(get_next_update_interval(20.2324, 10), 60)

    # Given: Get a 0 as the execution time, static interval is 5
    # When: get next interval
    # Then: Return default interval, 5
    def test_get_interval_zero(self):
        self.assertEqual(get_next_update_interval(0, 5), 5)

    # Given: Get a 0.000000 as the execution time, static interval is 5
    # When: get next interval
    # Then: Return default interval, 5
    def test_get_interval_zero_long(self):
        self.assertEqual(get_next_update_interval(0.000000, 5), 5)

    # Given: Wrongly get a negative number(-0.000001) as the execution time, static interval is 5
    # When: get next interval
    # Then: Return default interval, 5
    def test_get_interval_negative(self):
        self.assertEqual(get_next_update_interval(-0.000001, 5), 5)

    # Given: Wrongly get a negative number(-10.000001) as the execution time, static interval is 5
    # When: get next interval
    # Then: Return default interval, 5
    def test_get_interval_negative_slow(self):
        self.assertEqual(get_next_update_interval(-10.000001, 5), 5)
