#!/usr/bin/env python3

from typing import List, Optional

import datetime
import hashlib
import json
import pathlib
import re

import discord

from timestuff import utcnow, fromtime

CURRENT = "/home/aj/P/bitcoin/faucet-discord/requests/current"

class Requests:
    RE_FILE = re.compile(r"^\d+-\d+[.]\d+-([0-9a-f]{64})[.]json")

    def __init__(self):
        self.path = pathlib.Path(CURRENT)

    def create(self, interaction: discord.Interaction, address: str) -> Optional[dict]:
        t = fromtime(utcnow())
        d = dict(timestamp=t,
                 interaction_id=interaction.id,
                 guild_id=interaction.guild_id,
                 user_id=interaction.user.id,
                 user_name=interaction.user.name,
                 user_created=fromtime(interaction.user.created_at),
                 address=address)
        j = json.dumps(d).encode('utf8')
        h = hashlib.sha256(j).hexdigest()
        filename = self.path / (t + "-" + h + ".json")
        try:
            with filename.open("xb") as f:
                f.write(j)
            d["filename"] = filename.name
            return d
        except FileExistsError:
            return None

    def read(self) -> List[dict]:
        result = []
        for fname in self.path.iterdir():
             m = self.RE_FILE.match(fname.name)
             if m is None:
                 continue
             d = fname.read_bytes()
             h = hashlib.sha256(d).hexdigest()
             if h != m.group(1):
                 continue
             s = json.loads(d.decode('utf8'))
             if not isinstance(s, dict):
                 continue
             s["filename"] = fname.name
             result.append(s)
        return result

if __name__ == "__main__":
    for r in Requests().read():
        print(r)
