#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import parse

from client_node import ClientNode
from tooling import mk_results_dir
ClientNode.KEY_DIR = "real_keypairs/"

def main():
    parser = argparse.ArgumentParser(
        prog="streamer_torture",
        description="Solana validator Simulation",
        epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros",
    )
    parser.add_argument("hosts", type=str, help="file with staked accounts")

    parser.add_argument(
        "--duration", type=float, help="how long to run the test for", default=3.0
    )
    parser.add_argument("--target", type=str, help="target validator", default="72.46.85.181:8004")
    parser.add_argument(
        "--num_connections",
        type=int,
        help="number of connections per client",
        default=1,
    )
    parser.add_argument("--tx-size", type=int, help="Transaction size", default=1000)

    args = parser.parse_args()

    mk_results_dir()
    configs = {"duration": args.duration, "tx-size": args.tx_size}


    client_identities = [
        line.strip().split(" ")[0].strip() for line in open(args.hosts, "r").readlines()
    ]
    client_nodes = [ClientNode(pubkey=host_id) for host_id in client_identities]

    for i, node in enumerate(client_nodes):
        configs[node.pubkey] = {"latency": None}
        node.run_agave_client(
                target=args.target,
                num_connections=args.num_connections,
                duration=args.duration,
                tx_size=args.tx_size,
            )
    json.dump(configs, open("results/config.json", "w"))
    print("========Waiting for clients=======")
    for node in client_nodes:
        node.wait()

    subprocess.run("sudo chmod a+rw -R ./results/", shell=True, text=True, check=True)



    parse.main(args.hosts)



if __name__ == "__main__":
    main()


