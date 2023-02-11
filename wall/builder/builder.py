import logging
import os
import threading
from wall import settings


LOGGER = logging.getLogger(__name__)


def init_history():
    LOGGER.info("Initializing history")
    History.build()


class History:
    profiles = {}

    @staticmethod
    def build():
        if settings.IS_MULTI_THREADED:
            builder = MultiThreadedHistoryBuilder()
            logging.info("Building the walls with MultiThreadedHistoryBuilder")
        else:
            builder = SimpleHistoryBuilder()
            logging.info("Building the walls with SimpleHistoryBuilder")
        data = builder.read_data()
        builder.build(data)

    @staticmethod
    def amount_per_profile_per_day(section, day):
        if section not in History.profiles:
            return 0
        if day not in History.profiles[section]:
            return 0
        return History.profiles[section][day] * settings.FOOT_VOLUME

    @staticmethod
    def price_per_profile_per_day(section, day):
        if section not in History.profiles:
            return 0
        if day not in History.profiles[section]:
            return 0
        return History.profiles[section][day] * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def price_per_day(day):
        total = 0
        for section, history in History.profiles.items():
            if day not in history:
                continue
            total += history[day]
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def overall():
        total = 0
        for section, history in History.profiles.items():
            for day, amount in history.items():
                total += amount
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE


class HistoryBuilder:
    @classmethod
    def read_data(cls, path=None):
        if path is None:
            path = settings.WALL_FILE

        LOGGER.info("Reading initial walls from '{}'.".format(path))
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

        LOGGER.info("The are {} wall sections.".format(counter - 1))

        return data

    def build(self, data):
        raise NotImplementedError()


class SimpleHistoryBuilder(HistoryBuilder):
    def build(self, data):
        day = 1
        History.profiles = {}
        for section in data:
            History.profiles[section] = {}

        while True:
            amount_added = 0
            for profile, sections in data.items():
                for idx, height in enumerate(sections):
                    if height >= settings.WALL_HEIGHT:
                        continue

                    if day not in History.profiles[profile]:
                        History.profiles[profile][day] = 0
                    data[profile][idx] += 1
                    History.profiles[profile][day] += 1
                    amount_added += 1

            if amount_added == 0:
                break
            day += 1


class MultiThreadedHistoryBuilder(HistoryBuilder):
    def __init__(self):
        self._partitions = []
        self._profile_locks = {}

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

    def _make_partitions(self, data):
        LOGGER.info("Preparing partitions.")
        self._partitions = []
        for profile, sections in data.items():
            for idx, section in enumerate(sections):
                partition = []
                for height in range(section, settings.WALL_HEIGHT):
                    partition.append(height + 1)
                self._partitions.append({
                    "profile": profile,
                    "section": idx + 1,
                    "data": partition,
                })
        LOGGER.info("Partitions ready.")

    def build(self, data):
        History.profiles = {}
        self._make_partitions(data)
        self._prepare_locks(data)
        workers = []
        for k in range(settings.THREADS_NUMBER):
            workers.append(BuilderThread(k + 1, self))

        for w in workers:
            w.start()

        for w in workers:
            w.join()


class BuilderThread(threading.Thread):
    def __init__(self, idx, builder):
        super().__init__()
        self._builder = builder
        self._day = 1
        self._idx = idx

    def run(self):
        LOGGER.info("Starting build worker {} ...".format(self._idx))

        while True:
            partition = self._builder.get_next_partition()
            if partition is None:
                break

            for height in partition["data"]:
                LOGGER.info("On day {} build worker {} extended section {} of profile {} to {} feet.".format(
                    self._day, self._idx, partition["section"], partition["profile"], height
                ))
                self._builder.build_profile(partition["profile"], self._day)
                self._day += 1

        LOGGER.info("Build worker {} is ready.".format(self._idx))
