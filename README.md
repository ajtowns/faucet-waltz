
Yet another bitcoin faucet, designed for signet and discord

 * `payout.py` reads json files in `requests/current`, adding them to its
   `payouts/audit.sqlite` database, makes payouts as requested
   provided users don't repeat requests too frequently, and updates
   `payouts/status.json` regularly

 * `discordbot.py` interfaces with discord to create json requests when
   the `/request` command is used, to provide a user's request history
   when `/history` is used, and to provide a quick update about the
   faucet status when `/status` is used. It maintains a `requests/recent.sqlite`
   db of recent requests, and moves completed requests from `requests/current`
   to `requests/complete/YYYY/MM-DD/`.
