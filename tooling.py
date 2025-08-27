
from subprocess import Popen, getstatusoutput
from contextlib import contextmanager
import subprocess
import time
import signal
from typing import IO, Union
from mininet.node import Host
import os
import fcntl
import json

def set_nonblocking(file_obj):
    fd = file_obj.fileno()  # Get the file descriptor
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)  # Get current flags
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)  # Set non-blocking mode


@contextmanager
def watchdog(max_time_min: int):
    print(f"Arming watchdog for {max_time_min} min in case we kill networking...")
    status, out = getstatusoutput(f'echo "reboot" | at now+{max_time_min}min')
    if status != 0:
        print(f"Will not proceed without a watchdog, error {out}")
        exit(1)
    try:
        yield None
    finally:
        status, out = getstatusoutput("atrm $(atq | cut -f1)")
        if status != 0:
            print(f"Could not kill watchdog, error {out}")
            print("Run 'sudo atrm $(atq | cut -f1)' manually to avoid node reboot!")
            exit(1)
        print("Watchdog killed successfully")


def write_entry_script(host: Host):
    name = f"shell_{host.name}.sh"
    print(f"PID of {host.name} = {host.pid}, source {name} for shell access")
    with open(name, "w") as f:
        f.write(f"sudo mnexec -a {host.pid} bash\n")
    os.chmod(name, 0o777)


def gracefully_stop(handle: Popen):
    print(f"Trying to stop process {handle.pid} {handle.args}")
    if isinstance(handle, CRDS_Node):
        handle.exit()
    handle.send_signal(signal.SIGINT)
    try:
        handle.wait(10.0)
    except subprocess.TimeoutExpired:
        handle.terminate()
        time.sleep(1.0)
        handle.kill()


class CRDS_Node:
    def __init__(self, host: Host, cmd: str):
        self.cmd = cmd
        self.pipe = host.popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               bufsize=1,  # Line-buffered
                               universal_newlines=True)
        assert self.pipe.stdin is not None
        assert self.pipe.stdout is not None
        self.stdin: IO = self.pipe.stdin
        self.stdout: IO = self.pipe.stdout
        set_nonblocking(self.stdout)
        for i in range(10):
            rv = self.out()
            if not rv:
                time.sleep(0.1)
            else:
                rv = json.loads(rv[0])
                self.pubkey = rv["start_node"]
                break
        else:
            raise RuntimeError(f"Process {cmd} on host {host} startup failure!")

    def exit(self):
        self.send("exit")

    def __getattr__(self, attr: str):
        return getattr(self.pipe, attr)

    def help(self):
        """Call the help on the node"""
        self.send("help")

    def send(self, msg: Union[str, dict], poll=True) -> list[str]:
        """Send message to the node. Message could be a string or json."""
        if isinstance(msg, dict):
            msg = json.dumps(msg)
        try:
            self.stdin.write(msg + "\n")
        except Exception as e:
            print("Can not send, process is dead")
            return []
        if poll:
            time.sleep(0.1)
            return self.out()
        else:
            return []

    def insert_contact_info(self, address: str, keypair: str = ""):
        self.out()
        ci = {"address": address}
        if keypair:
            ci['keypair'] = keypair
        self.send(json.dumps({"InsertContactInfo": ci}))
        return self.out()

    def peers(self):
        """Get list of CRDS peers"""
        self.out()
        self.send('{"Peers":null}', poll=False)
        time.sleep(0.2)
        rv = self.out()[0]
        return json.loads(rv)

    def out(self) -> list[str]:
        """Get pending output from the pipe"""
        rv = []
        try:
            while self.stdout.readable:
                msg = self.stdout.readline()
                if len(msg):
                    rv.append(msg)
                else:
                    break
        except BlockingIOError:
            pass
        return rv


def run_repl(gossip, ip_addresses, net=None, topo=None, break_link=None, repair_link=None):
    banner = (
        "\n==================== Interactive Gossip Shell ====================\n"
        "Available variables:\n"
        "  gossip         - list of all CRDS_Node instances\n"
        "  ip_addresses   - list of their IP addresses\n\n"
        "Available network functions:\n"
        "  break_link('region1', 'region2')\n"
        "  repair_link('region1', 'region2')\n\n"
        "Examples:\n"
        "  gossip[0].peers()             # show known peers of node 0\n"
        "  gossip[1].insert_contact_info('10.0.0.42:8001')\n"
        "  gossip[2].help()              # ask the node to return help\n"
        "  gossip[3].send('exit')        # manually stop a node\n\n"
        "Exiting this shell will shut down the network.\n"
        "==================================================================\n"
    )
    mapping = {"gossip": gossip, "ip_addresses": ip_addresses, "net": net, "topo": topo}
    try:
        import IPython
        IPython.embed(banner1=banner, local_ns=mapping)
    except ImportError:
        print("[WARNING] IPython not found. Falling back to basic shell.")
        print("You are now in a basic interactive mode.\n")
        print("Available variables:")
        print("  gossip         -> list of all CRDS_Node objects")
        print("  ip_addresses   -> list of their IP addresses")
        print("\nExamples:")
        print("  gossip[0].help()                      # Show help for first node")
        print("  gossip[1].send('{\"Peers\":null}')      # Ask node 1 for peers")
        print("  gossip[2].insert_contact_info('10.0.0.2:8001')  # Insert peer info")
        print("  exit                                  # Exit this interactive session")
        print("\nNote: Use Ctrl+D to exit or type 'exit'\n")

        try:
            while True:
                code = input(">>> ")
                if code.strip() == "exit":
                    break
                try:
                    exec(code, mapping)
                except Exception as e:
                    print(f"Error: {e}")
        except EOFError:
            pass

def enable_l2_mode(net):
    print("=== L2 mode for OVS switches ===")
    for sw in net.switches:
        if sw.name.startswith("s"):  # only real switches
            print(f" {sw.name}: fail_mode=standalone")
            sw.cmd(f"ovs-vsctl set Bridge {sw.name} fail_mode=standalone")
