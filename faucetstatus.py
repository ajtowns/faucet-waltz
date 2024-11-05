#!/usr/bin/env python3

from typing import Dict, List

import dataclasses
import datetime
import decimal
import json
import os

from timestuff import totime, fromtime

FILE_STATUS = "./payouts/status.json"
FILE_STATUS_TMP = "./payouts/status.json.tmp"

@dataclasses.dataclass
class Status:
    last_check: datetime.datetime
    request_frequency: datetime.timedelta
    faucet_balance: decimal.Decimal
    faucet_address: str
    current_payouts: Dict[str, List[str]]  # txid to list of filenames
    current_rejects: List[str] # list of filenames

    @classmethod
    def from_json(cls, jsondata):
        d = json.loads(jsondata)
        return cls(
            last_check=totime(d["last_check"]),
            request_frequency=datetime.timedelta(seconds=d["request_frequency"]),
            faucet_balance=decimal.Decimal(d["faucet_balance"]),
            faucet_address=d["faucet_address"],
            current_payouts=d["current_payouts"],
            current_rejects=d["current_rejects"],
        )

    def to_json(self) -> str:
        d = dataclasses.asdict(self)
        d["last_check"] = fromtime(d["last_check"])
        d["request_frequency"] = d["request_frequency"].total_seconds()
        d["faucet_balance"] = str(d["faucet_balance"])
        return json.dumps(d)

    def write(self) -> None:
        f = open(FILE_STATUS_TMP, "w")
        f.write(self.to_json())
        f.flush()
        f.close()
        os.rename(FILE_STATUS_TMP, FILE_STATUS)

    @classmethod
    def read(cls):
        return cls.from_json(open(FILE_STATUS, "r").read())
