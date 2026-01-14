#!/usr/bin/env python3
import argparse

import matplotlib.pyplot as plt
import numpy as np
import os
from itertools import cycle
from datatypes import (
    server_local_dtype,
    server_record_dtype,
    client_local_dtype,
    client_record_dtype,
)

np.set_printoptions(suppress=True)


def main(hosts_file:str, show:bool):

    transactions_per_second: dict[str, dict] = {}
    total_sent_bytes_per_host = {}
    total_sent_transactions_per_client = {}
    stakes = {}

    client_transport_stats: dict[str, np.ndarray[client_local_dtype]] = {}

    base_time = 2**62
    last_end_time = 0
    # Processing binary files
    for binary_file in [f for f in os.listdir("results") if f.endswith(".bin")]:
        path = os.path.join("results", binary_file)
        host = binary_file.split("-")[0]
        print(f"Loading {path}")
        if "server" in binary_file:
            host = "SERVER"
            data = np.fromfile(path, dtype=server_record_dtype).astype(
                server_local_dtype
            )

        else:
            data = np.fromfile(path, dtype=client_record_dtype).astype(
                client_local_dtype
            )
            data = data[data["connection_id"] == 0]
            client_transport_stats[host] = data
            print(f"{host}, {data['udp_tx'][-1]}")
            total_sent_bytes_per_host[host] = data["udp_tx"][-1]
            total_sent_transactions_per_client[host] = len(data["time"])

        start = data["time"].min()
        base_time = min(base_time, start)
        end = data["time"].max()
        last_end_time = max(last_end_time, end)

        bin_size = 1000 * 10  # 10 ms bins
        bins = np.arange(start, end + bin_size, bin_size)
        counts, edges = np.histogram(data["time"], bins=bins)
        transactions_per_second[host] = {"timeline": edges[0:-1], "TPS": counts * 100}

    colormap = plt.cm.tab20 if len(transactions_per_second) > 10 else plt.cm.tab10
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 14))
    ax1_2 = ax1.twinx()
    color_cycle = cycle(colormap.colors)
    for host, host_data in client_transport_stats.items():
        color = next(color_cycle)
        # ax1.plot(
        #     (host_data["time"] - base_time) / 1e6,
        #     host_data["udp_tx"],
        #     label=f"{host[0:7]}-udp_tx",
        #     linestyle="-",
        #     color=color,
        # )

        ax1_2.plot(
            (host_data["time"] - base_time) / 1e6,
            host_data["congestion_window"] / 1e3,
            label=f"{host[0:7]}-congestion_window",
            linestyle=":",
            color=color,
        )
        # ax1.plot(
        #     (host_data["time"] - base_time) / 1e6,
        #     host_data["congestion_events"] ,
        #     label=f"{host[0:7]}-congestions",
        #     linestyle="-",
        #     color=color,
        #     )
        ax1.plot(
            (host_data["time"] - base_time) / 1e6,
            host_data["lost_packets"] ,
            label=f"{host[0:7]}-lost_pkts",
            linestyle="-",
            color=color,
            )

    ax1.set_xlim([0, (last_end_time - base_time) / 1e6])
    ax1_2.set_xlim([0, (last_end_time - base_time) / 1e6])
    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Lost packets")
    ax1_2.set_ylabel("Congestion window (dotted) KB", color="r")
    ax1.grid(True)

    color_cycle = cycle(colormap.colors)
    ax2_2 = ax2.twinx()
    ax2_2.set_ylabel("Server-side TPS (black)", color="black")
    for host, data in transactions_per_second.items():
        color = next(color_cycle)
        print(host, color)
        linewidth = 1
        ax = ax2
        if host == "SERVER":
            color = "black"
            linewidth = 2
            ax = ax2_2
        ax.plot(
            (data["timeline"] - base_time) / 1e6,
            data["TPS"],
            label=f"{host[0:7]}",
            linestyle="-",
            linewidth=linewidth,
            color=color,
        )

    ax2_2.set_xlim([0, (last_end_time - base_time) / 1e6])
    ax2.set_xlim([0, (last_end_time - base_time) / 1e6])
    ax2.set_ylabel("Transactions per Second")

    with open(hosts_file) as f:
        for line in f:
            stakes[line.split(" ")[0]] = int(line.split(" ")[1])

    # Normalizing values for bars
    transactions_sum = sum(total_sent_transactions_per_client.values())
    for k, v in total_sent_transactions_per_client.copy().items():
        total_sent_transactions_per_client[k] = float(v) / transactions_sum * 100

    bytes_sent_sum = sum(total_sent_bytes_per_host.values())
    for k, v in total_sent_bytes_per_host.copy().items():
        total_sent_bytes_per_host[k] = float(v) / bytes_sent_sum * 100.0

    stake_sum = sum(stakes.values())
    for k, v in stakes.items():
        stakes[k] = v / stake_sum * 100

    for host in stakes.keys():
        print(
            f"Host:{host}\nStake:{stakes[host]:.1f}%\nVolume:{total_sent_bytes_per_host[host]:.1f}%\nTransactions:{[total_sent_transactions_per_client[host]][0]:.1f}%\n"
        )

    stakes_bottom = 0
    volume_bottom = 0
    tps_bottom = 0
    color_cycle = cycle(colormap.colors)
    for host in stakes.keys():
        color = next(color_cycle)
        label = f"{host[0:7]}"
        ax3.bar("Stakes", stakes[host], bottom=stakes_bottom, color=color, label=label)
        ax3.bar(
            "Transactions",
            total_sent_transactions_per_client[host],
            bottom=tps_bottom,
            color=color,
            label=label,
        )
        ax3.bar(
            "Traffic volume",
            total_sent_bytes_per_host[host],
            bottom=volume_bottom,
            color=color,
            label=label,
        )
        tps_bottom += total_sent_transactions_per_client[host]
        volume_bottom += total_sent_bytes_per_host[host]
        stakes_bottom += stakes[host]

    ax3.set_ylabel("SWQOS analysis")
    handles, labels = ax3.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax3.legend(
        by_label.values(),
        by_label.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=3,  # optional: spread entries in a row
    )

    plt.title("Transmission, Reception, TPS")
    plt.savefig("TPS.png")
    if show:
        plt.show(block=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="plotter script",
        description="plotter thing for results",
        epilog="If you encounter some bug, I wish you a luck ©No-Manuel Macros",
    )
    parser.add_argument("hosts", type=str, help="file with staked accounts")
    parser.add_argument("--show", action="store_true", help="Show plot for interactive ")
    args = parser.parse_args()
    main(args.hosts, args.show)

