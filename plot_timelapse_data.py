#!/usr/bin/env python3
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

    # Processing csv files
    for csv_file in csv_files:
        host = csv_file.split('-')[0]
        df = pd.read_csv(os.path.join("results", csv_file))
        df['host'] = host
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
        binary_data = pd.concat([binary_data, df], ignore_index=True)

    color_cycle_csv = cycle(plt.cm.tab10.colors)
    color_cycle_binary = cycle(plt.cm.Set2.colors)

    fig, (ax1, ax2) = plt.subplots(2,1,figsize=(12, 12))

    for host in csv_data["host"].unique():
        host_csv_data = csv_data[csv_data["host"] == host]
        color = next(color_cycle_csv)
        ax1.plot(host_csv_data["time_stamp"] / 1_000_000, host_csv_data["udp_tx"], label=f"{host}-udp_tx", linestyle='-', color=color)
        ax1.plot(host_csv_data["time_stamp"] / 1_000_000, host_csv_data["udp_rx"], label=f"{host}-udp_rx", linestyle='--', color=color)

    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Bytes")
    ax1.legend(loc="upper left")
    ax1.grid(True)

    for host in binary_data["host"].unique():
        host_binary_data = binary_data[binary_data["host"] == host]
        color = next(color_cycle_binary)
        ax2.plot(host_binary_data["timeline"], host_binary_data["TPS"], label=f"{host}-TPS", linestyle='-', color=color)

    ax2.set_ylabel("Transactions per Second")
    ax2.legend(loc="upper right")

    plt.title("Transmission, Reception, TPS")
    plt.savefig("TPS.png")

if __name__ == "__main__":
    main()
