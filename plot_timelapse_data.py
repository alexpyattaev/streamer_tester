#!/usr/bin/env python3
from re import L
import matplotlib.pyplot as plt
import csv
import numpy as np
import pandas as pd
import os
from itertools import cycle
np.set_printoptions(suppress=True)

server_record_dtype = np.dtype([
    ("id",  "S32"),   # 32-byte pubkey
    ("size", np.uint64),
    ("time", np.uint32),
])

def main():
    files = os.listdir("results")
    csv_files = [f for f in files if f.endswith('.csv')]
    binary_files = [f for f in files if f.endswith('.bin')]

    csv_columns = ["host", "udp_tx", "udp_rx", "time_stamp"]
    binary_columns = ["host", "transactions", "TPS"]

    csv_data = pd.DataFrame(columns=csv_columns)
    binary_data = pd.DataFrame(columns=binary_columns)

    tx_volume = {}
    tps_rcv = {}
    stakes = {}

    # Processing csv files
    for csv_file in csv_files:
        host = csv_file.split('-')[0]
        df = pd.read_csv(os.path.join("results", csv_file))
        df['host'] = host
        tx_volume[host] = df["udp_tx"].iloc[-1]
        csv_data = pd.concat([csv_data, df], ignore_index=True)

    # Processing binary files
    for binary_file in binary_files:
        path = os.path.join("results", binary_file)
        host = binary_file.split('-')[0]
        if "server" in  binary_file:
            timestamps = np.fromfile(path, dtype=server_record_dtype)['time'] / 1_000_000
        else:
            timestamps = np.fromfile(os.path.join("results", binary_file), dtype=np.uint32) / 1_000_000

        start = timestamps.min()
        end = timestamps.max()
        bin_size = 0.01
        bins = np.arange(start, end+bin_size, bin_size) # 10 ms granularity
        counts, edges = np.histogram(timestamps, bins=bins)
        transactions_per_second = counts * 100
        df = pd.DataFrame({
            "host": host,
            "timeline": edges[0:-1],
            "TPS": transactions_per_second
        })
        if not "server" in binary_file:
            tps_rcv[host] = df["TPS"].sum().astype(int)
        binary_data = pd.concat([binary_data, df], ignore_index=True)

    color_cycle_csv = cycle(plt.cm.tab10.colors)
    color_cycle_binary = cycle(plt.cm.Set2.colors)
    color_cycle_stake = cycle(plt.cm.tab20.colors)
    fig, (ax1, ax2, ax3) = plt.subplots(3,1,figsize=(12, 12))

    for host in csv_data["host"].unique():
        host_csv_data = csv_data[csv_data["host"] == host]
        color = next(color_cycle_csv)
        ax1.plot(host_csv_data["time_stamp"] / 1_000_000, host_csv_data["udp_tx"], label=f"{host[0:7]}-udp_tx", linestyle='-', color=color)
        ax1.plot(host_csv_data["time_stamp"] / 1_000_000, host_csv_data["udp_rx"], label=f"{host[0:7]}-udp_rx", linestyle='--', color=color)

    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Bytes")
    ax1.legend(loc="upper left")
    ax1.grid(True)

    for host in binary_data["host"].unique():
        host_binary_data = binary_data[binary_data["host"] == host]
        color = next(color_cycle_binary)
        ax2.plot(host_binary_data["timeline"], host_binary_data["TPS"], label=f"{host[0:7]}", linestyle='-', color=color)

    ax2.set_ylabel("Transactions per Second")
    ax2.legend(loc="upper right")

    with open("solana_pubkeys.txt") as f:
        for line in f:
            stakes[line.split(' ')[0]] = int(line.split(' ')[1])

    #Normalizing values for bars
    transactions_sum = sum(tps_rcv.values())
    for k,v in tps_rcv.items():
        tps_rcv[k]=v/transactions_sum * 100

    tx_sum = sum(tx_volume.values())
    for k,v in tx_volume.items():
        tx_volume[k]=v/tx_sum * 100

    stake_sum = sum(stakes.values())
    for k,v in stakes.items():
        stakes[k]=v/stake_sum * 100


    for host in stakes.keys():
        print(f"Host:{host}\nStake:{stakes[host]:.1f}%\nVolume:{tx_volume[host]:.1f}%\nTransactions:{[tps_rcv[host]][0]:.1f}%\n")

    stakes_bottom = 0
    volume_bottom = 0
    tps_bottom = 0
    for host in stakes.keys():
        color = next(color_cycle_stake)
        ax3.bar("Stakes",stakes[host], bottom=stakes_bottom, color=color, label = host)
        ax3.bar("Transactions",tps_rcv[host], bottom=tps_bottom, color=color, label = host)
        ax3.bar("Traffic volume",tx_volume[host], bottom=volume_bottom, color=color, label = host)
        tps_bottom += tps_rcv[host]
        volume_bottom += tx_volume[host]
        stakes_bottom += stakes[host]

    ax3.set_ylabel("SWQOS analysis")

    plt.title("Transmission, Reception, TPS")
    plt.savefig("TPS.png")

if __name__ == "__main__":
    main()
