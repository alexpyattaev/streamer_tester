#!/usr/bin/python
import argparse

import numpy as np
from base58 import b58encode, b58decode
import os
import pprint
import json
import re
from datatypes import server_record_dtype


def main(hosts_file:str):


    config = json.load(open("results/config.json"))
    pprint.pprint(config)
    duration = config["duration"]

    try:
        server_data = np.fromfile("results/serverlog.bin", dtype=server_record_dtype)
        print(f"Server captured {len(server_data)} transactions ({int(len(server_data) / duration)} TPS)")
    except:
        server_data = None
        print("Server state not available")

    stakes = [
        re.split(r"[\s]+", line.strip())
        for line in open(hosts_file).readlines()
    ]
    for v in stakes:
        print(v)
    stakes = {b58decode(a): int(b) for a, b in stakes}


    per_client = {}
    for file in os.listdir("results"):
        if file.endswith("summary"):
            num = np.fromfile(f"./results/{file}", dtype=np.uint64)
            per_client[file.split(".")[0]] = num[0]

    datapoints = open("datapoints.csv", "a+")
    for id in stakes:
        b58_id = b58encode(id).decode("ascii")
        sent = per_client[b58_id]

        if server_data is not None:
            got = (server_data["id"] == id).sum()
            print(
            f"{b58_id}: {sent=} {got=} lost {int(sent - got)} ({int(got / duration)} TPS)"
            )

        else:
            got = sent
            print(
                f"{b58_id}: {sent=}   ({int(sent / duration)} TPS)"
            )

        datapoints.write(f"{config[b58_id]['latency']} {stakes[id]} {got / duration}\n")
    datapoints.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="parse script",
        description="parser thing for results",
        epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros",
    )
    parser.add_argument("hosts", type=str, help="file with staked accounts")
    args = parser.parse_args()
    main(args.hosts)
