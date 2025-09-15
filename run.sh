#!/bin/bash
set -x -e


T="sudo ./main.py solana_pubkeys.txt --duration=3.0 --server=./swqos"
N=5

make_and_run() {
    local tx_sz=$1
    shift
    local prefix=$1
    shift
    rm -f datapoints.csv
    ./make_stakes.py --min-stake=0 --max-stake=10000 "$N"

    for lat in "$@"; do
        $T --latency="$lat" --tx-size="$tx_sz"
    done

    python plot_3d.py $prefix "$tx_sz" bytes
    rm -f datapoints.csv
}

# configure what latencies to test
LATS=(5 50 100)

# run for different transaction sizes
make_and_run 176 new "${LATS[@]}"
make_and_run 512 new "${LATS[@]}"
make_and_run 1024 new "${LATS[@]}"


T='sudo ./main.py solana_pubkeys.txt  --duration=3.0 --server=./swqos_current'

# run for different transaction sizes
make_and_run 176 old "${LATS[@]}"
make_and_run 512 old "${LATS[@]}"
make_and_run 1024 old "${LATS[@]}"
