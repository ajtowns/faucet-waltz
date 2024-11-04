#!/usr/bin/env python

import datetime

import sqlalchemy as sa

class TimeStamp(sa.types.TypeDecorator):
    impl = sa.types.DateTime

    def process_bind_param(self, value: datetime.datetime, dialect):
        if value is None: return None
        return value.astimezone(datetime.timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None: return None
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)

        return value.astimezone(datetime.timezone.utc)
