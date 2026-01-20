#!/usr/bin/env python3

import subprocess
import requests
import threading
import logging
import sys
from pathlib import Path

# ---- configuration ----
RPC_URL = "https://api.mainnet-beta.solana.com"
CLIENT_BIN = "./client"  # path to your client binary
#PUBKEYS=["1KXvrkPXwkGF6NK1zyzVuJqbXfpenPVPP6hoiK9bsK3", "23U4mgK9DMCxsv2StC4y2qAptP25Xv5b2cybKCeJ1to3"]
PUBKEYS = open("watchlist.txt").read().splitlines()
LOG_DIR = Path("results")
# -----------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

LOG_DIR.mkdir(exist_ok=True)

def fetch_all_tpu_quic_addrs(pubkeys: list[str]) -> dict[str, str]:
    """
    Returns a mapping {pubkey: 'ip:port'} for TPU QUIC endpoints.
    Resolves all pubkeys using a single getClusterNodes RPC call.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getClusterNodes",
    }
    r = requests.post(RPC_URL, json=payload, timeout=10)
    r.raise_for_status()

    # Build pubkey -> tpuQuic map from RPC response
    nodes = {}
    for node in r.json()["result"]:
        pk = node.get("pubkey")
        tpu_quic = node.get("tpuQuic")
        if pk and tpu_quic:
            nodes[pk] = tpu_quic

    # Validate requested pubkeys
    result = {}
    missing = []
    for pk in pubkeys:
        addr = nodes.get(pk)
        if not addr:
            missing.append(pk)
        else:
            result[pk] = addr

    if missing:
        logging.warning(
            "Missing TPU QUIC address for pubkeys: "
            + ", ".join(missing)
        )

    return result



def run_client(pubkey: str, addr:str):

    log_path = LOG_DIR / pubkey
    logging.info("Starting client for %s -> %s", pubkey, addr)
    args = f"{CLIENT_BIN} --target {addr} --max-bitrate-bps 10e3 --host-name {pubkey}  --num-connections 1 --tx-size 512"
    with open(log_path, "wb") as f:
        proc = subprocess.Popen(
            args.split(),
            stdout=f,
            stderr=f,
        )
        rc = proc.wait()

    logging.info(
        "Client for %s terminated with exit code %d",
        pubkey,
        rc,
    )


def main():
    threads = []
    tpu_addrs = fetch_all_tpu_quic_addrs(PUBKEYS)

    for pk, addr  in tpu_addrs.items():
        t = threading.Thread(target=run_client, args=(pk,addr), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == "__main__":
    if len(sys.argv) != 1:
        print("No arguments expected; configure script constants instead", file=sys.stderr)
        sys.exit(1)
    main()
