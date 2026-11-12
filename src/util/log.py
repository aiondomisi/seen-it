from _pydatetime import datetime


def log(log: str) -> None:
    print(f"[{datetime.now().strftime("%b %d %Y - %H:%M:%S'")}] {log}")
