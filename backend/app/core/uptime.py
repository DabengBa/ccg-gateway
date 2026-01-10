import time

START_TIME = 0


def init_start_time():
    global START_TIME
    START_TIME = int(time.time())


def get_uptime() -> int:
    return int(time.time()) - START_TIME
