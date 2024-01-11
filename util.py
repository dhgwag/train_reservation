import datetime


def get_nowtime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
