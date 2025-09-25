#!/usr/bin/python
import numpy as np
from base58 import b58encode, b58decode
import os
import pprint
import json
import re


def main():
    config = json.load(open("results/1024/config.json"))
    pprint.pprint(config)
    duration = config["duration"]

    record_dtype = np.dtype(
        [
            ("id", "S32"),  # 32-byte pubkey
            ("size", np.uint64),
            ("time", np.uint32),
        ]
    )

    data = np.fromfile("results/1024/serverlog.bin", dtype=record_dtype)
    stakes = [
        re.split(r"[\s]+", l.strip()) for l in open("solana_pubkeys.txt").readlines()
    ]
    for v in stakes:
        print(v)
    stakes = {b58decode(a): int(b) for a, b in stakes}

    print(f"Server captured {len(data)} transactions ({int(len(data) / duration)} TPS)")

    per_client = {}
    for file in os.listdir("results"):
        if file.endswith("summary"):
            num = np.fromfile(f"./results/1024/{file}", dtype=np.uint64)
            per_client[file.split(".")[0]] = num[0]

    datapoints = open("datapoints.csv", "a")
    for id in stakes:
        b58_id = b58encode(id).decode("ascii")
        sent = per_client[b58_id]
        got = (data["id"] == id).sum()
        print(
            f"{b58_id}: {sent=} {got=} lost {int(sent - got)} ({int(got / duration)} TPS)"
        )
        if abs(sent - got) > 10:
            raise RuntimeError()
        datapoints.write(f"{config[b58_id]['latency']} {stakes[id]} {got / duration}\n")
    datapoints.close()


if __name__ == "__main__":
    main()
