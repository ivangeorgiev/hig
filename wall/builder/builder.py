import os
import logging
from wall import settings


LOGGER = logging.getLogger(__name__)


def init_history():
    LOGGER.info("Initializing history")
    History.build()


class History:
    sections = {}

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
    def amount_per_section_per_day(section, day):
        if section not in History.sections:
            return 0
        if day not in History.sections[section]:
            return 0
        return History.sections[section][day] * settings.FOOT_VOLUME

    @staticmethod
    def price_per_section_per_day(section, day):
        if section not in History.sections:
            return 0
        if day not in History.sections[section]:
            return 0
        return History.sections[section][day] * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def price_per_day(day):
        total = 0
        for section, history in History.sections.items():
            if day not in history:
                continue
            total += history[day]
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def overall():
        total = 0
        for section, history in History.sections.items():
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
        History.sections = {}
        for section in data:
            History.sections[section] = {}

        while True:
            amount_added = 0
            for section, parts in data.items():
                for idx, height in enumerate(parts):
                    if height >= settings.WALL_HEIGHT:
                        continue

                    if day not in History.sections[section]:
                        History.sections[section][day] = 0
                    data[section][idx] += 1
                    History.sections[section][day] += 1
                    amount_added += 1

            if amount_added == 0:
                break
            day += 1


class MultiThreadedHistoryBuilder(HistoryBuilder):
    pass
