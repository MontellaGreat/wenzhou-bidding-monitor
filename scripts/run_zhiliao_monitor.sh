#!/usr/bin/env bash
set -euo pipefail

export ZLBX_APP_ID="202603081480343542189522944"
export ZLBX_APP_SECRET="dbb6bb44741c4066a4025e284145fce0"
export ZLBX_TOKEN="8e0a67b6-8928-4de8-922b-d0921796ade0"
export ZLBX_DETAIL_LIMIT="6"
export ZLBX_LIMIT="30"
export ZLBX_DAYS="7"

cd /home/admin/.openclaw/workspace
python3 scripts/wenzhou_bidding_zhiliao.py
