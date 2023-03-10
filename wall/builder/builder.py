import logging
import os
import threading
from wall import settings


LOGGER = logging.getLogger(__name__)


class History:
    profiles = {}

    @staticmethod
    def build():
        LOGGER.info("Building history ...")
        if settings.IS_MULTI_THREADED:
            builder = MultiThreadedHistoryBuilder()
            logging.info("Building the walls with MultiThreadedHistoryBuilder ...")
        else:
            builder = SimpleHistoryBuilder()
            logging.info("Building the walls with SimpleHistoryBuilder ...")
        data = builder.read_data()
        builder.build(data)

    @staticmethod
    def amount_per_profile_per_day(profile, day):
        if profile not in History.profiles:
            return 0
        if day not in History.profiles[profile]:
            return 0
        return History.profiles[profile][day] * settings.FOOT_VOLUME

    @staticmethod
    def price_per_profile_per_day(profile, day):
        if profile not in History.profiles:
            return 0
        if day not in History.profiles[profile]:
            return 0
        return History.profiles[profile][day] * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def price_per_day(day):
        total = 0
        for history in History.profiles.values():
            if day not in history:
                continue
            total += history[day]
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def overall():
        total = 0
        for history in History.profiles.values():
            for day, amount in history.items():
                total += amount
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE


class HistoryBuilder:
    @classmethod
    def read_data(cls, path=None):
        if path is None:
            path = settings.WALL_FILE

        LOGGER.info("Reading wall profiles from '{}' ...".format(path))
        if not os.path.exists(path):
            raise FileNotFoundError("Initial walls from '{}' can not be found.".format(path))

        data = {}
        counter = 1
        with open(path, "r") as fp:
            line = fp.readline().strip()
            while line:
                sections = line.split()
                data[counter] = [int(s) for s in sections]
                line = fp.readline().strip()
                counter += 1

        LOGGER.info("The are {} wall profiles.".format(counter - 1))

        return data

    def __init__(self):
        self._day = 1
        self._partitions = []

    @property
    def day(self):
        return self._day

    def is_ready(self):
        raise NotImplementedError()

    def build_profile(self, profile, day):
        raise NotImplementedError()

    def build(self, data):
        raise NotImplementedError()

    def _make_partitions(self, data):
        LOGGER.info("Preparing partitions ...")
        self._partitions = []
        for profile, sections in data.items():
            for idx, section in enumerate(sections):
                self._partitions.append({
                    "profile": profile,
                    "section": idx + 1,
                    "height": section,
                })
        LOGGER.info("Partitions ready.")


class SimpleHistoryBuilder(HistoryBuilder):
    def __init__(self):
        super().__init__()
        self._amount_added = 0

    def is_ready(self):
        return self._amount_added == 0

    def build_profile(self, profile, day):
        if profile not in History.profiles:
            History.profiles[profile] = {}
        if day not in History.profiles[profile]:
            History.profiles[profile][day] = 0
        History.profiles[profile][day] += 1

    def build(self, data):
        History.profiles = {}
        self._day = 1
        self._make_partitions(data)

        while True:
            self._amount_added = 0
            for partition in self._partitions:
                if partition["height"] >= settings.WALL_HEIGHT:
                    continue

                partition["height"] += 1
                self._amount_added += 1
                self.build_profile(partition["profile"], self.day)

            if self.is_ready():
                LOGGER.info("Ready. Wall was build in {} days.".format(self.day))
                break

            LOGGER.info("On day {} the wall workers extended {} sections.".format(self.day, self._amount_added))
            self._day += 1


class MultiThreadedHistoryBuilder(HistoryBuilder):
    def __init__(self):
        super().__init__()
        self._profile_locks = {}
        self._schedule = {}
        self._barrier = None

    @property
    def schedule(self):
        return self._schedule

    @property
    def active_workers(self):
        result = 0
        for partition in self._schedule.values():
            if partition is not None:
                result += 1
        return result

    @property
    def barrier(self):
        return self._barrier

    def is_ready(self):
        return self.active_workers == 0

    def get_next_partition(self):
        try:
            return self._partitions.pop(0)
        except IndexError:
            return None

    def build_profile(self, profile, day):
        with self._profile_locks[profile]:
            if profile not in History.profiles:
                History.profiles[profile] = {}
            if day not in History.profiles[profile]:
                History.profiles[profile][day] = 0
            History.profiles[profile][day] += 1

    def _prepare_locks(self, data):
        self._profile_locks = {}
        for profile in data:
            self._profile_locks[profile] = threading.Lock()

    def build(self, data):
        History.profiles = {}
        self._make_partitions(data)
        self._prepare_locks(data)
        self._day = 1
        self._schedule = {}

        for idx in range(1, settings.THREADS_NUMBER + 1):
            self.schedule[idx] = self.get_next_partition()

        while not self.is_ready():
            for idx in range(1,  settings.THREADS_NUMBER + 1):
                if self.schedule[idx] and self.schedule[idx]["height"] >= settings.WALL_HEIGHT:
                    self.schedule[idx] = self.get_next_partition()
                    if self.schedule[idx] is None:
                        LOGGER.info("Build worker {} is ready.".format(idx))
                    else:
                        LOGGER.info("Build worker {} moves to profile {}, section {}.".format(
                            idx, self.schedule[idx]["profile"], self.schedule[idx]["section"]))

            self._barrier = threading.Barrier(self.active_workers + 1)
            for idx in range(1,  settings.THREADS_NUMBER + 1):
                if self.schedule[idx] is None:
                    continue

                w = BuilderThread(idx, self)
                w.start()

            self._barrier.wait()
            self._day += 1


class BuilderThread(threading.Thread):
    @property
    def idx(self):
        return self._idx

    @property
    def builder(self):
        return self._builder

    def __init__(self, idx, builder):
        super().__init__()
        self._builder = builder
        self._idx = idx

    def run(self):
        partition = self.builder.schedule[self.idx]
        partition["height"] += 1

        LOGGER.info("On day {} build worker {} extended section {} of profile {} to {} feet.".format(
            self.builder.day, self.idx, partition["section"], partition["profile"], partition["height"]
        ))
        self.builder.build_profile(partition["profile"], self.builder.day)
        self.builder.barrier.wait()
