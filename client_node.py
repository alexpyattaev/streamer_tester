import subprocess


class ClientNode:
    KEY_DIR="solana_keypairs/"
    def __init__(self, pubkey: str, latency: int=0, mininet_host = None):
        self.pubkey = pubkey
        self.latency = latency
        self.mininet_host = mininet_host
        self.proc = None

    def run_iperf_client(self, target: str, duration: float, tx_size: int):
        args = f"iperf3 -l{tx_size}b -c {target} -t{int(duration)} -u -b 1G"
        print(f"running {args}...")
        self.proc = self.mininet_host.popen(
            f"{args}",
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_agave_client(
        self, target: str, duration: float, tx_size: int, num_connections: int
    ):
        args = f"./mock_server/target/release/client --target {target} --duration {duration} --host-name {self.pubkey} --staked-identity-file {self.KEY_DIR}/{self.pubkey}.json --num-connections {num_connections} --tx-size {tx_size}"# --disable-congestion"

        print(f"running {args}...")
        if self.mininet_host is not None:
            self.proc = self.mininet_host.popen(
                    f"{args}",
                    shell=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
            )
        else:
            self.proc = subprocess.Popen(f"{args}",
                                         shell=True,
                                         text=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)

    def wait(self):
        if self.proc is None:
            return
        print(f"==== Waiting for client {self.pubkey} latency {self.latency}")
        print(self.proc.stdout.read(), end="")  # pyright:ignore
        print(self.proc.stderr.read(), end="")  # pyright:ignore
        self.proc.wait()
        print("======")
        self.proc = None
