#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
from subprocess import call
import argparse
from tooling import watchdog
import subprocess
import json
import sys
import os


class ClientNode():
    def __init__(self, pubkey:str, latency:int, host):
        self.pubkey = pubkey
        self.latency = latency
        self.host = host

    def run_agave_client(self, target:str, duration:float, tx_size:int):
        args = f"./mock_server/target/release/client --target {target} --duration {duration} --host-name {self.pubkey} --staked-identity-file solana_keypairs/{self.pubkey}.json --num-connections 1 --tx-size {tx_size} --disable-congestion"

        print(f"running {args}...")
        # self.tcpdump = subprocess.Popen(f"{cli} tcpdump -i veth_cli-2 -w capture_client.pcap",
        #                         shell=True, text=True,
        #                         stdout=subprocess.PIPE,
        #                         stderr=subprocess.PIPE,
        #                         )
        self.proc = self.host.popen(f"{args}",
                                shell=True, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                )

    def wait(self):
        print(f"==== Terminating client {self.pubkey} latency {self.latency}")
        print(self.proc.stdout.read(), end="") # pyright:ignore
        print(self.proc.stderr.read(), end="") # pyright:ignore
        self.proc.wait()
        # self.tcpdump.terminate()
        # print("Waiting on tcpdump")
        # self.tcpdump.wait()
        print("======")

def main():
    parser = argparse.ArgumentParser(prog='streamer_torture',description="Solana validator Simulation",
                                     epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros")
    parser.add_argument('hosts',type=str, help='file with staked accounts')
    parser.add_argument('--loss-percentage',type=int, default=0, help='0-100 allowed')
    parser.add_argument('--duration',type=float,help='how long to run the test for',default=3.0)
    parser.add_argument('--latency',type=int,help='override latency',default=50)
    parser.add_argument('--tx-size',type=int,help='Transaction size',default=1000)

    args = parser.parse_args()

    if args.loss_percentage not in range(0,100):
        print("run ./sosim -h'")
        exit()

    client_identities = [l.strip().split(' ')[0].strip() for l in open(args.hosts,'r').readlines()]
    client_nodes = []


    net, server_node, client_nodes = topology(client_identities, args)



    print("Environment is up.\nRunning a server")

    cmd = f"./swqos --test-duration {args.duration+2.0} --stake-amounts solana_pubkeys.txt --bind-to 0.0.0.0:8000"

    # srv_tcpdump = subprocess.Popen(f"{cli} tcpdump -i srv-br -w capture_server.pcap",
    #                        shell=True, text=True,
    #                        stdout=subprocess.PIPE,
    #                        stderr=subprocess.PIPE,
    #                        )
    print(f"Running {cmd}")
    server = server_node.popen(cmd,
        shell=True, text=True,
        stdout=subprocess.DEVNULL,
        stderr=sys.stdout,
        env = os.environ.copy(),
        bufsize=1
    )

    for node in client_nodes:
        node.run_agave_client(target =server_node.IP()+":8000", duration=  args.duration, tx_size=args.tx_size)

    try:
        server.wait(timeout=args.duration+3.0)
    except:
        server.kill()
        print("Server killed")
    server.wait()
    print("========Stopping clients=======")
    for node in client_nodes:
        node.wait()

    # srv_tcpdump.terminate()
    # print("Waiting on server tcpdump")
    # srv_tcpdump.wait()
    subprocess.run("sudo chmod a+rw -R ./results/", shell=True, text=True, check=True)

    #print("*** Running CLI")
    #CLI(net)

    print("*** Stopping network")
    net.stop()

def topology(client_identities, args):
    configs = {"duration":args.duration, "tx-size":args.tx_size}
    net = Mininet(controller=OVSController, link=TCLink)
    switch = net.addSwitch('s1')
    _ = net.addController('c0')
    server = net.addHost('server')
    net.addLink(server, switch, delay='1ms', bw=1000)   # server side (fast)
    client_nodes = []
    print("*** Creating clients")

    for idx, host_id in enumerate(client_identities, start = 2):
        host = net.addHost(f'client{idx}')
        link_delay = args.latency
        configs[host_id] = {"latency":link_delay}
        net.addLink(host, switch, delay=f'{link_delay}ms', bw=10000, limit=2000000)
        client_nodes.append(ClientNode(pubkey=host_id, latency=link_delay, host=host))


    print("*** Starting network")
    net.start()

    print(f"Server IP is {server.IP()}")
    for client in client_nodes:
        print(client.host.IP())

    print("*** Testing connectivity")
    #net.pingAll()
    json.dump(configs, open("results/config.json", "w"))
    return net, server, client_nodes

if __name__ == '__main__':
    setLogLevel('info')
    with watchdog(60):
        print("\n[DEBUG] Cleaning Mininet state (mn -c)")
        call(["sudo", "mn", "-c"])
        main()

    import parse
    parse.main()
