#!/usr/bin/python
import numpy as np
from base58 import b58encode, b58decode
import os
import pprint
import json
import re

def main():
    config = json.load(open("/home/sol/streamer_tester/config.json"))
    pprint.pprint(config)
    duration = config['duration']
    # Build a quick lookup of pubkey -> latency from config.json
    default_latency = config.get('latency')
    client_latency_by_pubkey = {
        c.get('pubkey'): c.get('latency', default_latency)
        for c in config.get('clients', [])
        if c.get('pubkey')
    }

    record_dtype = np.dtype([
        ("id",  "S32"),   # 32-byte pubkey
        ("size", np.uint64),
        ("time", np.uint32),
    ])

    data = np.fromfile("/home/sol/swqos_test/results/serverlog.bin", dtype=record_dtype)
    stakes = [ re.split(r'[\s]+', l.strip()) for l in open("/home/sol/swqos_test/solana_pubkeys.txt").readlines()]
    for v in stakes:
        print(v)
    stakes = {b58decode(a):int(b) for a,b in stakes}

    print(f"Server captured {len(data)} transactions ({int(len(data)/duration)} TPS)")

    per_client = {}
    for file in os.listdir("/home/sol/swqos_test/results"):
        if file.endswith("summary"):
            num = np.fromfile(f"/home/sol/swqos_test/results/{file}", dtype=np.uint64)
            per_client[file.split(".")[0]]= num[0]

    datapoints = open("datapoints.csv","a")
    for id in stakes:
        b58_id = b58encode(id).decode('ascii')
        sent = per_client.get(b58_id)
        if sent is None:
            print(f"Warning: no summary found for {b58_id}, skipping")
            continue
        got = (data['id'] == id).sum()
        print(f"{b58_id}: {sent=} {got=} lost {int(sent - got)} ({int(got/duration)} TPS)")
        if abs(sent-got) > 1000:
            raise RuntimeError()
        latency_value = client_latency_by_pubkey.get(b58_id, default_latency)
        datapoints.write(f"{latency_value} {stakes[id]} {got/duration}\n")
    datapoints.close()


if __name__ == '__main__':
    main()
