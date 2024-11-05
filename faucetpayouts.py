#!/usr/bin/env python3

from typing import List, Optional, Tuple

import datetime
import json

import sqlalchemy as sa
from sqlmodel import Session, SQLModel, Field, Relationship, create_engine, select

from sqlalchemytime import TimeStamp

DB = "sqlite:///./payouts/audit.sqlite"

class Payout(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime.datetime = Field(sa_column=sa.Column(TimeStamp(),
                                                             index=True,
                                                            ))
    txid: str = Field(index=True, unique=True)

    requests: List["Request"] = Relationship(back_populates="payout")

class Request(SQLModel, table=True):
    __table_args__ = (sa.Index("idx_userid_time", "userid", "timestamp"),
                      sa.Index("idx_payout_userid", "payout_id", "userid"),
                     )

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(index=True, unique=True)
    timestamp: datetime.datetime = Field(sa_column=sa.Column(TimeStamp(),
                                                             index=True,
                                                            ))
    username: str = Field(index=True)
    userid: int
    address: str = Field(index=True)
    payout_id: int | None = Field(default=None, foreign_key="payout.id")

    payout: Payout | None = Relationship(back_populates="requests")

class PayoutDB:
    def __init__(self, echo=False):
        self.engine = create_engine(DB, echo=echo)
        SQLModel.metadata.create_all(self.engine)

    def last_payout(self, userid : int) -> Tuple[Optional[Request], Optional[Payout]]:
        with Session(self.engine) as session:
            results = session.exec(select(Request).where(Request.userid == userid).where(Request.payout_id != None).order_by(Request.timestamp.desc()))
            p, f = None, results.first()
            if f is not None and f.payout_id is not None:
                p = session.get(Payout, f.payout_id)
            return f, p

    def seen(self, filename : str) -> Tuple[bool, Optional[str]]:
        with Session(self.engine) as session:
            results = session.exec(select(Request).where(Request.filename == filename))
            r = results.first()
            if r is None:
                return False, None
            elif r.payout is None:
                return True, None
            else:
                return True, r.payout.txid

    def add_bad_reqs(self, reqs : List[Request]):
        with Session(self.engine) as session:
            for r in reqs:
                session.add(r)
            session.commit()
            for r in reqs:
                session.refresh(r)

    def add_paid_reqs(self, now, txid : str, reqs : List[Request]):
        with Session(self.engine) as session:
            payout = Payout(timestamp=now, txid=txid, requests=reqs)
            session.add(payout)
            session.commit()
            for r in reqs:
                session.refresh(r)


