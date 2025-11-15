#!/usr/bin/env python3
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


def main():
    transactions_per_second: dict[str, dict] = {}
    total_sent_bytes_per_host = {}
    total_sent_transactions_per_client = {}
    stakes = {}

    client_transport_stats: dict[str, np.ndarray[client_local_dtype]] = {}

    base_time = 2**62
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
            client_transport_stats[host] = data
            print(f"{host}, {data['udp_tx'][-1]}")
            total_sent_bytes_per_host[host] = data["udp_tx"][-1]
            total_sent_transactions_per_client[host] = len(data["time"])

        base_time = min(base_time, data["time"].min())
        start = data["time"].min()
        end = data["time"].max()

        bin_size = 1000 * 10  # 10 ms bins
        bins = np.arange(start, end + bin_size, bin_size)
        counts, edges = np.histogram(data["time"], bins=bins)
        transactions_per_second[host] = {"timeline": edges[0:-1], "TPS": counts * 100}

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 14))
    ax1_2 = ax1.twinx()
    color_cycle = cycle(plt.cm.tab20.colors)
    for host, host_data in client_transport_stats.items():
        color = next(color_cycle)
        ax1.plot(
            host_data["time"],
            host_data["udp_tx"] / 1e6,
            label=f"{host[0:7]}-udp_tx",
            linestyle="-",
            color=color,
        )
        # ax1.plot(
        #     host_data["time"],
        #     host_data["udp_rx"],
        #     label=f"{host[0:7]}-udp_rx",
        #     linestyle="--",
        #     color=color,
        # )
        # congestions = np.diff(host_data["congestion_events"], prepend=[0]) != 0
        ax1_2.plot(
            host_data["time"] / 1e6,
            host_data["congestion_events"],
            label=f"{host[0:7]}-congestions",
            linestyle=":",
            markerfacecolor="red",
            markeredgecolor="red",
            color=color,
        )

    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("MBytes")
    ax1_2.set_ylabel("Congestion events", color="r")
    ax1.grid(True)

    color_cycle = cycle(plt.cm.tab20.colors)
    ax2_2 = ax2.twinx()
    ax2_2.set_ylabel("Server-side TPS", color="black")
    for host, data in transactions_per_second.items():
        color = next(color_cycle)
        linewidth = 1
        ax = ax2
        if host == "SERVER":
            color = "black"
            linewidth = 2
            ax = ax2_2
        ax.plot(
            data["timeline"] / 1e6,
            data["TPS"],
            label=f"{host[0:7]}",
            linestyle="-",
            linewidth=linewidth,
            color=color,
        )

    ax2.set_ylabel("Transactions per Second")

    with open("solana_pubkeys.txt") as f:
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
    color_cycle = cycle(plt.cm.tab20.colors)
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


if __name__ == "__main__":
    main()
