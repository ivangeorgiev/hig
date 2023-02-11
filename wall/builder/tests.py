from django.test import TestCase
from wall import settings
from .builder import History


class TestHistoryBuilder(TestCase):
    def test_simple_builder(self):
        settings.IS_MULTI_THREADED = False
        settings.WALL_FILE = settings.BASE_DIR / "data.txt"
        History.build()

        self.assertEqual(History.amount_per_profile_per_day(1, 1), 585)
        self.assertEqual(History.price_per_profile_per_day(1, 1), 1111500)
        self.assertEqual(History.price_per_day(1), 3334500)
        self.assertEqual(History.overall(), 32233500)

    def test_multi_threaded_builder(self):
        settings.IS_MULTI_THREADED = True
        settings.THREADS_NUMBER = 2
        settings.WALL_FILE = settings.BASE_DIR / "data.txt"
        History.build()

        self.assertEqual(History.amount_per_profile_per_day(1, 1), 390)
        self.assertEqual(History.price_per_profile_per_day(1, 1), 741000)
        self.assertEqual(History.price_per_day(1), 741000)
        self.assertEqual(History.overall(), 32233500)
