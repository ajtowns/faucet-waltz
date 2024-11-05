#!/usr/bin/env python3

from typing import Dict, List, Set

import datetime
import decimal
import json
import logging
import re
import subprocess
import sys
import time

import faucetpayouts
import faucetrequests
import faucetstatus

from timestuff import utcnow, totime

CMD=f"bitcoin-cli -rpcwallet= -signet"

MAX_PER_TX=500
BTC_PER_TX=decimal.Decimal("0.2")
BTC_PER_OUT=decimal.Decimal("0.05")
QUANTIZE=decimal.Decimal(10)**-5
BTC_MIN = decimal.Decimal("0.00001")

REQUEST_FREQUENCY = datetime.timedelta(hours=1)
BALANCE_FREQUENCY = datetime.timedelta(minutes=30)

FILE_STATUS = "/home/aj/P/bitcoin/faucet-discord/payouts/status.json"
FILE_STATUS_TMP = "/home/aj/P/bitcoin/faucet-discord/payouts/status.json.tmp"

class Worker:
    RE_TXID = re.compile(r'^[0-9a-f]{64}$')

    def __init__(self):
        self.reqs = faucetrequests.Requests()
        self.paid = faucetpayouts.PayoutDB()
        self.balance = decimal.Decimal(0)
        self.balance_bump = utcnow()

    def get_balance(self):
        n = utcnow()
        if n >= self.balance_bump:
            self.balance_bump = n + BALANCE_FREQUENCY
            b = subprocess.run(f"{CMD} getbalance", shell=True, capture_output=True)
            if b.returncode == 0:
                self.balance = decimal.Decimal(b.stdout.strip().decode('utf8'))
        return self.balance

    def loop(self):
        while True:
            self.dowork()
            time.sleep(60)

    def dowork(self) -> bool:
        more_work = False
        now = utcnow()
        current = self.reqs.read()

        payouts : Dict[str, List[str]] = {}
        rejects : List[str] = []
        bad : List[faucetpayouts.Request] = []
        good : List[faucetpayouts.Request] = []
        good_addresses : Set[str] = set()
        for r in current:
            if len(good) >= MAX_PER_TX:
                more_work = True
                break
            s, tx = self.paid.seen(r["filename"])
            if s:
                l = payouts.setdefault(tx, []) if tx else rejects
                l.append(r["filename"])
                continue
            req = faucetpayouts.Request(filename=r["filename"], timestamp=totime(r["timestamp"]), username=r["user_name"], userid=r["user_id"], address=r["address"])
            lastr, lastp = self.paid.last_payout(r["user_id"])
            if lastr: print(lastr.timestamp, now)
            if lastr is not None and lastr.timestamp + REQUEST_FREQUENCY >= now:
                logging.debug(f"ignoring request to {req.address} for {req.username}; wait longer")
                bad.append(req)
                continue
            if req.address in good_addresses:
                logging.debug(f"ignoring request for duplicate address {req.address}")
                bad.append(req)
                continue
            logging.info(f"queuing payment to {req.address} for {req.username}")
            good.append(req)
            good_addresses.add(req.address)

        if bad:
            self.paid.add_bad_reqs(bad)
            rejects.extend(b.filename for b in bad)

        if good:
            payout_txid = self.generate_payout(good)
            if payout_txid is not None:
                self.paid.add_paid_reqs(now, payout_txid, good)
                payouts[payout_txid] = [g.filename for g in good]
            logging.info(f"made payout {payout_txid}")

        status = faucetstatus.Status(
            last_check=now,
            request_frequency=REQUEST_FREQUENCY,
            faucet_balance=self.get_balance(),
            faucet_address="unknown",
            current_payouts=payouts,
            current_rejects=rejects,
        )
        status.write()
        return more_work

    def generate_payout(self, requests):
        amount = min(BTC_PER_OUT, (BTC_PER_TX/len(requests)).quantize(QUANTIZE, rounding=decimal.ROUND_DOWN))
        amount = str(amount)

        create_in = '[]\n' + json.dumps([{entry.address: amount} for entry in requests])

        proc = subprocess.Popen(f"{CMD} -stdin createrawtransaction", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, encoding='utf8')
        proc.stdin.write(create_in)
        proc.stdin.close()
        unfunded = proc.stdout.read()

        proc = subprocess.Popen(f"{CMD} -stdin fundrawtransaction", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, encoding='utf8')
        out, errs = proc.communicate(unfunded + '{"include_unsafe": true}\n')
        if errs:
             return None
        funded = json.loads(out)["hex"]

        proc = subprocess.Popen(f"{CMD} -stdin signrawtransactionwithwallet", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, encoding='utf8')
        out, errs = proc.communicate(funded)
        signed = json.loads(out)["hex"]

        result = subprocess.run(f"{CMD} -stdin sendrawtransaction", input=signed, shell=True, encoding='utf8', capture_output=True)

        txid = result.stdout.strip()
        if self.RE_TXID.match(txid):
            return txid
        else:
            return None

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    worker = Worker()
    worker.loop()

if __name__ == "__main__":
    main()
