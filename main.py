#!/bin/python3
import subprocess
import argparse
import time
import sys
import os
import unicodedata
import json

def strip_nonprintable(s):
    return ''.join(
        ch for ch in s
        if unicodedata.category(ch)[0] != "C"
    )



class ClientNode():
    def __init__(self, ip:str, pubkey:str, target_ip:str, latency:int):
        self.ip = ip
        self.pubkey = pubkey
        self.latency = latency
        self.target_ip = target_ip

    def run_agave_client(self, duration:float, tx_size:int):
        cli = f"sudo --preserve-env=RUST_LOG ip netns exec client{self.pubkey[0:8]}"
        args = f"./mock_server/target/release/client --target {self.target_ip}:8000 --duration {duration} --host-name {self.pubkey} --staked-identity-file solana_keypairs/{self.pubkey}.json --num-connections 1 --tx-size {tx_size} --disable-congestion"

        print(f"running {args}...")
        self.proc = subprocess.Popen(f"{cli} {args}",
                                shell=True, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                )

    def wait(self):
        print(f"==== Terminating client {self.pubkey} latency {self.latency}")
        print(self.proc.stdout.read(), end="") # pyright:ignore
        print(self.proc.stderr.read(), end="") # pyright:ignore
        self.proc.wait()
        print("======")

def main():
    #Link qualities
    link_delays = [35,100,200]
    parser = argparse.ArgumentParser(prog='streamer_torture',description="Solana validator Simulation",
                                     epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros")
    parser.add_argument('hosts',type=str, help='file with staked accounts')
    parser.add_argument('--loss-percentage',type=int, default=0, help='0-100 allowed')
    parser.add_argument('--duration',type=float,help='how long to run the test for',default=3.0)
    parser.add_argument('--latency',type=int,help='override latency',default=0)
    parser.add_argument('--tx-size',type=int,help='Transaction size',default=1000)

    args = parser.parse_args()

    if args.loss_percentage not in range(0,100):
        print("run ./sosim -h'")
        exit()

    client_identities = [l.strip().split(' ')[0].strip() for l in open(args.hosts,'r').readlines()]
    client_nodes = []

    configs = {"duration":args.duration, "tx-size":args.tx_size}
    subprocess.run("sudo ./server.sh", shell=True)
    for idx, host_id in enumerate(client_identities, start = 2):
        if args.latency == 0:
            link_delay = link_delays[(idx%len(link_delays)-1)]
        else:
            link_delay = args.latency
        configs[host_id] = {"latency":link_delay}
        client_nodes.append(ClientNode(f"10.0.1{idx}",host_id,"10.0.1.1", latency=link_delay))
        subprocess.run(f"sudo ./client.sh {host_id[0:8]} {idx} {link_delay} {args.loss_percentage}",shell=True)

    json.dump(configs, open("results/config.json", "w"))


    print("Environment is up.\nRunning a server")
    cli = "sudo --preserve-env=RUST_LOG ip netns exec server"
    # args = f"./mock_server/target/debug/server --listen 10.0.1.1:8009 --receive-window-size 630784  --max-concurrent-streams 512 --stream-receive-window-size 1232"
    cmd = f"./swqos --test-duration {args.duration+1.0} --stake-amounts solana_pubkeys.txt --bind-to 0.0.0.0:8000"

    print(f"Running {cmd}")
    server = subprocess.Popen(f"{cli} {cmd}",
        shell=True, text=True,
        stdout=subprocess.DEVNULL,
        stderr=sys.stdout,
        env = os.environ.copy(),
        bufsize=1
   )

    for node in client_nodes:
        node.run_agave_client(args.duration, args.tx_size)

    try:
        server.wait(timeout=args.duration+2.0)
    except:
        server.kill()
        print("Server killed")
    server.wait()
    time.sleep(0.1)
    print("========Stopping clients=======")
    for node in client_nodes:
        node.wait()

    subprocess.run("sudo chmod a+rw -R ./results/", shell=True, text=True, check=True)

if __name__ == '__main__':
    main()
    import parse
    parse.main()
