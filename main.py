#!/bin/python3
import subprocess
import argparse
import time
from random import randint

class ClientNode():
    def __init__(self, ip:str, pubkey:str, target_ip:str):
        self.ip = ip
        self.pubkey = pubkey
        self.target_ip = target_ip

    def run_agave_client(self):
        cli = f"sudo ip netns exec client{self.pubkey[0:8]}"
        args = f"./mock_server/target/release/client --target {self.target_ip}:8000 --duration 3.3 --host-name {self.pubkey} --staked-identity-file solana_keypairs/{self.pubkey}.json"
        self.proc = subprocess.Popen(f"{cli} {args}",
                                shell=True, text=True, stdout=subprocess.DEVNULL
                                )

def main():
    #Link qualities
    link_delays = [35,100,200]
    delay_distributions = [15,45,50]
    parser = argparse.ArgumentParser(prog='sosim',description="Solana validator Simulation",
                                     epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros")
    parser.add_argument('hosts',type=str, help='file with staked accounts')
    parser.add_argument('loss_percentage',type=int,help='0-100 allowed')

    args = parser.parse_args()
    if args.loss_percentage not in range(0,100):
        print("run ./sosim -h'")
        exit()

    client_identities = [l.strip().split(' ')[0].strip() for l in open(args.hosts,'r').readlines()]
    client_nodes = []

    subprocess.run("sudo ./server.sh", shell=True)
    for idx, host_id in enumerate(client_identities, start = 2):
        link_delay = link_delays[(idx%len(link_delays)-1)]
        delay_distribution = delay_distributions[((idx+randint(0,2))%len(delay_distributions)-1)]
        client_nodes.append(ClientNode(f"10.0.1{idx}",host_id,"10.0.1.1"))
        subprocess.run(f"sudo ./client.sh {host_id[0:8]} {idx} {link_delay} {delay_distribution} {args.loss_percentage}",shell=True)


    print("Environment is up.\nRunning a server")
    cli = "sudo ip netns exec server"
    # args = f"./mock_server/target/debug/server --listen 10.0.1.1:8009 --receive-window-size 630784  --max-concurrent-streams 512 --stream-receive-window-size 1232"
    args = "./swqos --test-duration 3.4 --stake-amounts solana_pubkeys.txt --bind-to 0.0.0.0:8000"
    server = subprocess.Popen(f"{cli} {args}",
        shell=True, text=True)#, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
   # )
    print("Running clients")

    for node in client_nodes:
        node.run_agave_client()
    print("Clients are up")

    time.sleep(3.5)
    server.kill()
    print("Server killed")
    server.wait()
    for node in client_nodes:
        node.proc.wait()
    subprocess.run("sudo chmod a+rw -R ./results/", shell=True, text=True, check=True)

if __name__ == '__main__':
    main()
