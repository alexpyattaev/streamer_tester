#!/bin/python
import os
import subprocess
import pandas as pd
from collections import defaultdict

from debian.changelog import endline

TIME_SAMPLE = 10_000 #in microseconds



def csv_handler(file):
    columns = ["udp_tx", "udp_rx", "time_stamp"]
    data = pd.read_csv(file, skiprows=range(0, 1), sep=",", names=columns,
                       dtype={"udp_tx": int, "udp_rx": int, "time_stamp": int})

    return sample_csv(data)

def sample_csv(df):
    df_upd = pd.DataFrame({"udp_tx": [], "udp_rx": [], "time_stamp": []})
    df["time_stamp"] = (df["time_stamp"] // TIME_SAMPLE) * TIME_SAMPLE
    #set of all timestamps in dataframe
    timestamps = sorted(set(df["time_stamp"]))
    for timestamp in timestamps:
        try:
            rx_max = max(df.loc[df["time_stamp"].eq(timestamp), "udp_rx"])
            tx_max = max(df.loc[df["time_stamp"].eq(timestamp), "udp_tx"])
        except:
            continue

        #adding data to new dataframe
        frame = pd.DataFrame({"udp_tx": [tx_max], "udp_rx": [rx_max], "time_stamp": [timestamp]})
        df_upd = pd.concat([df_upd, frame], ignore_index=True)

    return df_upd

def sum_csv(dfs):
    final_df = pd.DataFrame(columns=["udp_tx","udp_rx","time_stamp"])
    for k,v in {"udp_tx": int, "udp_rx": int, "time_stamp": int}.items():
        final_df.astype({k:v})

    timestamps = []
    for df in dfs:
        timestamps.extend(df["time_stamp"].tolist())

    timestamps = sorted(set(timestamps))
    for timestamp in timestamps:
        values_to_sum = defaultdict(list)
        for df in dfs:
            try:
                rx_max = max(df.loc[df["time_stamp"].eq(timestamp), "udp_rx"])
                tx_max = max(df.loc[df["time_stamp"].eq(timestamp), "udp_tx"])
            except:
                continue

            values_to_sum["udp_rx"].append(rx_max)
            values_to_sum["udp_tx"].append(tx_max)

        tx_sum = sum(values_to_sum["udp_tx"])
        rx_sum = sum(values_to_sum["udp_rx"])
        frame = pd.DataFrame({"udp_tx": [int(tx_sum)], "udp_rx": [int(rx_sum)], "time_stamp": [int(timestamp)]})

        final_df = pd.concat([final_df, frame], ignore_index=True)


    return final_df



def main():
    #Nested directories list
    directories = os.listdir("results")

    #Main data structure keypair[identity,"bin"/"csv"]:[data files names]
    identities = {}

    with open("solana_pubkeys.txt") as f:
        for line in f:
            identities[line.split(" ")[0], "csv"] = []
            identities[line.split(" ")[0], "bin"] = []

    for dir in directories:
        latencies = []
        path = "results/" + dir + "/"

        files = os.listdir(path)

        csv_files = [f for f in files if f.endswith(".csv")]
        binary_files = [f for f in files if f.endswith(".bin")]

        for id, _ in identities.keys():
            for file in csv_files:
                if id in file:
                    identities[id, "csv"].append(file)
                    lat = file.replace(".", " ").replace("-", " ").split()[2]
                    latencies.append(lat)
            for file in binary_files:
                if id in file:
                    identities[id, "bin"].append(file)

        latencies = set(latencies)

        for lat in latencies:
            csv_files = defaultdict(list)
            csv_dfs = defaultdict(list)
            for (id, data_type), files in identities.items():
                data_sources = set([f for f in files if lat in f])
                for file in data_sources:
                    if data_type == "csv":
                        csv_files[id].append(file)
                    else:
                        cmd = f"cat {path}{file} >> {path}{id}-{lat}.{data_type}"
                        print(f"CMD::{cmd}")
                        subprocess.run(cmd, shell=True, text=True)
                        subprocess.run(f"rm {path}{file}", shell=True, text=True)

            for id, files in csv_files.items():
                for file in files:
                    csv_dfs[id].append(csv_handler(path+file))
                df_to_write = sum_csv(csv_dfs[id])
                df_to_write.to_csv(f"{path}{id}-{lat}.csv",index=False)
                print(f"SAVED CSV FILE::{path}{id}-{lat}.csv")
            for id, files in csv_files.items():
                for file in files:
                    subprocess.run(f"rm {path}{file}", shell=True, text=True)


if __name__ == "__main__":
    main()
