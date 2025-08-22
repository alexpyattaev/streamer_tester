#!/bin/python3
import subprocess
import argparse
import time
from random import randint

class Node():
    def __init__(self, ip:str, label:str, target_ip:str):
        self.ip = ip
        self.label = label
        self.target_ip = target_ip

    def run_agave_client(self):
        cli = f"sudo ip netns exec client{self.label}"
        args = f"--target {self.target_ip}:8009 --duration 3.3 --host-name {self.label}"
        subprocess.Popen(f"{cli} ./mock_server/target/debug/client {args}",
                                shell=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
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

    hosts = [l.strip().split(' ')[0].strip() for l in open(args.hosts,'r').readlines()]

    subprocess.run("sudo ./server.sh", shell=True)
    for idx, host in enumerate(hosts, start =2 ):
        name = host[0:8]
        link_delay = link_delays[(idx%len(link_delays)-1)]
        delay_distribution = delay_distributions[((idx+randint(0,2))%len(delay_distributions)-1)]
        nodes.append(Node(f"10.0.1{idx}",name,"10.0.1.1"))
        subprocess.run(f"sudo ./client.sh {name} {idx} {link_delay} {delay_distribution} {args.loss_percentage}",shell=True)


    print("Environment is up.\nRunning a server")
    cli = f"sudo ip netns exec server"
    args = f"./mock_server/target/debug/server --listen 10.0.1.1:8009 --receive-window-size 630784  --max-concurrent-streams 512 --stream-receive-window-size 1232"
    args = f"./swqos --test-duration 10.0 --stake-amounts solana_pubkeys.txt"
    server = subprocess.Popen(f"{cli} {args}",
        shell=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("Running clients")

    for node in nodes:
        node.run_agave_client()
    print("Clients are up")

    time.sleep(3.5)
    server.kill()
    print("Server killed")
    subprocess.run("sudo chmod 666 ./results/*", shell=True, text=True)


if __name__ == '__main__':
    main()
