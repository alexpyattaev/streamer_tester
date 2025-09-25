from __future__ import print_function
import sys
import os
import subprocess
import time


def main():
    directories = os.listdir("results")
    identities = {}
    with open("solana_pubkeys.txt") as f:
        for line in f:
            identities[line.split(" ")[0], "csv"] = []
            identities[line.split(" ")[0], "bin"] = []

    for dir in directories:
        latencies = []
        work_dir = "results/" + dir + "/"
        path = work_dir
        print(path)
        files = os.listdir(path)
        csv_files = [f for f in files if f.endswith(".csv")]
        binary_files = [f for f in files if f.endswith(".bin")]
        for id, _ in identities.keys():
            for file in csv_files:
                if id in file:
                    identities[id, "csv"].append(file)
                    lat = file.replace(".", " ").replace("-", " ").split()[-2]
                    latencies.append(lat)
            for file in binary_files:
                if id in file:
                    identities[id, "bin"].append(file)

        latencies = set(latencies)

        for lat in latencies:
            for keys, files in identities.items():
                id, data_type = keys
                data_sources = set([f for f in files if lat in f])
                print(path)
                for file in data_sources:
                    if id == "csv":
                        cmd = f"tail -n +2 {path}{file} >> {path}{id}-{lat}.{data_type}"
                    else:
                        cmd = f"cat {path}{file} >> {path}{id}-{lat}.{data_type}"
                    print(cmd)
                    subprocess.run(cmd, shell=True, text=True)
                    # time.sleep(0.3)
                    # subprocess.run(f"rm {path}{file}", shell=True, text=True)


if __name__ == "__main__":
    main()
