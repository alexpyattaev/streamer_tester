#!/usr/bin/python
import numpy as np
from base58 import b58encode, b58decode
import os
import pprint
import json

def main():
    config = json.load(open("results/config.json"))
    pprint.pprint(config)
    duration = config['duration']

    record_dtype = np.dtype([
        ("id",  "S32"),   # 32-byte pubkey
        ("size", np.uint64),
        ("time", np.uint32),
    ])

    data = np.fromfile("results/serverlog.bin", dtype=record_dtype)
    stakes = [ l.split(' ') for l in open("solana_pubkeys.txt").readlines()]
    stakes = {b58decode(a):b for a,b in stakes}

    print(f"Server captured {len(data)} transactions ({int(len(data)/duration)} TPS)")

    per_client = {}
    for file in os.listdir("results"):
        if file.endswith("summary"):
            num = np.fromfile(f"./results/{file}", dtype=np.uint64)
            per_client[file.split(".")[0]]= num[0]

    for id in stakes:
        b58_id = b58encode(id).decode('ascii')
        sent = per_client[b58_id]
        got = (data['id'] == id).sum()
        print(f"{b58_id}: {sent=} {got=} lost {int(sent - got)} ({int(got/duration)} TPS)")

if __name__ == '__main__':
    main()
