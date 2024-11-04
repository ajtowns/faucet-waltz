#!/usr/bin/env python

import datetime

TIME_FMT = "%Y%m%d-%H%M%S.%f"

DELTA_UNITS = [("s", 60), ("m", 60), ("h", 24), ("d", 0)]

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def totime(s : str) -> datetime.datetime:
    return datetime.datetime.strptime(s, TIME_FMT).replace(tzinfo=datetime.timezone.utc)

def fromtime(dt : datetime.datetime) -> str:
    return dt.strftime(TIME_FMT)

def timedeltahuman(delta : datetime.timedelta) -> str:
    s = int(delta.total_seconds())
    if s <= 0:
        return f"{s}s"
    r = []
    for (sym, amt) in DELTA_UNITS:
        if amt == 0:
            n = s
        else:
            n = s % amt
            s = (s - n) // amt
        if n != 0:
            r.append(f"{n}{sym}")
    return "".join(reversed(r))
