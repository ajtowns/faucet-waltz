#!/usr/bin/env python3

from typing import Optional, Dict

import datetime
import json
import logging

from hashlib import sha256

import discord
import discord.ext.tasks
from discord import app_commands

import faucetrecent
import faucetrequests
import faucetstatus

from timestuff import timedeltahuman, totime, utcnow

TOKEN = open("DISCORD-TOKEN").read().strip()
PATH = './requests'
TXURL = "https://mempool.space/signet/tx/%s"

def txurl(txid : str) -> str:
    return TXURL % (txid,)

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)
        self.recent = faucetrecent.RecentDB()
        self.interactions : Dict[str, discord.Interaction] = {}

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        #self.tree.copy_global_to(guild=MY_GUILD)
        r = await self.tree.sync()
        print(f"sync result: {[sr.name for sr in r]}")

intents = discord.Intents.default()
client = MyClient(intents=intents)
requests = faucetrequests.Requests()

async def edit_orig_resp(req : str, **kwargs) -> None:
    if req not in client.interactions: return
    orig = await client.interactions[req].original_response()
    await orig.edit(**kwargs)

@discord.ext.tasks.loop(seconds=30)
async def cleanup():
    for s in list(client.interactions):
        if client.interactions[s].is_expired():
            del client.interactions[s]

    s = faucetstatus.Status.read()
    if s is None: return
    recent_cleanup = []
    for txid in s.current_payouts:
        for req in s.current_payouts[txid]:
            if requests.complete(req):
                logging.info(f"Successful payout of {req} via {txid}")
                await edit_orig_resp(req, content=None, embed=discord.Embed(description=f"Request [successful]({txurl(txid)})."))
                recent_cleanup.append((req, txid))
                del client.interactions[req]
    for req in s.current_rejects:
        if requests.complete(req):
            logging.info(f"Failed payout of {req}")
            if req in client.interactions:
                edit_orig_resp(req, content="Request for funds failed")
            recent_cleanup.append((req, None))
            del client.interactions[req]
    client.recent.complete_requests(recent_cleanup)

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logging.info('------')
    cleanup.start()

@client.tree.command()
@app_commands.describe(
    address='Signet address for funds (tb1...)',
)
async def request(interaction: discord.Interaction, address: str):
    """Requests funds from the faucet"""
    logging.info(f"Request for {interaction.user.name} to {address}")
    if (reqd := requests.create(interaction, address)):
        req = faucetrecent.RecentReq(
            filename=reqd["filename"],
            timestamp=totime(reqd["timestamp"]),
            user_name=reqd["user_name"],
            user_id=reqd["user_id"],
            address=reqd["address"],
        )
        assert isinstance(interaction.client, MyClient)
        interaction.client.recent.add_request(req)
        await interaction.response.send_message(f"Request for funds acknowledged", ephemeral=True)
        interaction.client.interactions[req.filename] = interaction
    else:
        await interaction.response.send_message(f"Request for funds ignored", ephemeral=True)

@client.tree.command()
async def status(interaction: discord.Interaction):
    s = faucetstatus.Status.read()
    lc = timedeltahuman(utcnow() - s.last_check)
    await interaction.response.send_message(f'Last check for payment requests {lc} ago, faucet balance {s.faucet_balance}.')

@client.tree.command()
async def history(interaction: discord.Interaction):
    assert isinstance(interaction.client, MyClient)
    h = interaction.client.recent.history(interaction.user.id)
    resp = []
    for hi in h:
        if hi.completed is not None:
            state = f"[paid]({txurl(hi.txid)})" if hi.txid else "failed"
            t = hi.completed
        else:
            state = "pending"
            t = hi.timestamp
        resp.append(f" * <t:{int(t.timestamp())}:R> funds to {hi.address} ({state})")
    if resp:
        e = discord.Embed(description=f"Your requests:\n\n{'\n'.join(resp)}\n")
        await interaction.response.send_message(embed=e, ephemeral=True)
    else:
        await interaction.response.send_message(content="You have not made any recent requests", ephemeral=True)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

client.run(TOKEN)

