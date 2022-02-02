import logging
from datetime import datetime


class TimeCount:
    def __init__(self, name):
        self.name = name
        self.stopwatch = datetime.now()

    def __del__(self):
        spent = datetime.now() - self.stopwatch
        logging.info(f'{self.name} completed: {spent}')


def timecount(func):
    def wrapper(*args, **kwargs):
        stopwatch = datetime.now()
        func(*args, **kwargs)
        spent = datetime.now() - stopwatch
        logging.info(f'{func.__name__} completed: {spent}')
    return wrapper
