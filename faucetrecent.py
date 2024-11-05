#!/usr/bin/env python3

from typing import List, Optional, Sequence, Tuple

import datetime
import json

import sqlalchemy as sa
from sqlmodel import Session, SQLModel, Field, Relationship, create_engine, select, update

from sqlalchemytime import TimeStamp
from timestuff import utcnow

DB = "sqlite:////home/aj/P/bitcoin/faucet-discord/requests/recent.sqlite"


class RecentReq(SQLModel, table=True):
    __table_args__ = (sa.Index("idx_userid_completed", "user_id", "completed"),
                     )

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(index=True, unique=True)
    timestamp: datetime.datetime = Field(sa_column=sa.Column(TimeStamp(),
                                                             index=True,
                                                            ))
    user_name: str
    user_id: int
    address: str
    completed: Optional[datetime.datetime] = Field(sa_column=sa.Column(TimeStamp(),
                                                                       index=True,
                                                                      ))
    txid: Optional[str]

class RecentDB:
    def __init__(self, echo=False):
        self.engine = create_engine(DB, echo=echo)
        SQLModel.metadata.create_all(self.engine)

    def history(self, user_id: int) -> Sequence[RecentReq]:
        with Session(self.engine) as session:
            results = session.exec(select(RecentReq).where(RecentReq.user_id == user_id).order_by(RecentReq.timestamp.desc()))
            return results.all()
        return []

    def latest(self, user_id: int) -> Optional[RecentReq]:
        with Session(self.engine) as session:
            results = session.exec(select(RecentReq).where(RecentReq.user_id == user_id).where(RecentReq.txid != None).order_by(RecentReq.timestamp.desc()))
            return results.first()

    def count_pending(self) -> int:
        with Session(self.engine) as session:
            results = session.exec(select(sa.func.count()).where(RecentReq.completed == None))
            return results.one()

    def add_request(self, req : RecentReq):
        assert req.completed is None
        with Session(self.engine) as session:
            session.add(req)
            session.commit()
            session.refresh(req)

    def complete_requests(self, filetxids : List[Tuple[str, Optional[str]]]):
        now = utcnow()
        with Session(self.engine) as session:
            for file, txid in filetxids:
                session.execute(update(RecentReq).where(RecentReq.filename == file).values(completed=now, txid=txid))
            session.commit()

