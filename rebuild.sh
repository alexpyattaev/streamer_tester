set -ex
cd ~/agave/streamer 
cargo build --release --examples
cd ~/streamer_torture/mock_server
cargo build --release
cd ../



TX_SIZE=512
N=30
C=1
T=10.0
#MAX="--max-tps 100000"
export RUST_LOG="info,solana_streamer=debug"
sudo --preserve-env=RUST_LOG  ./main.py solana_pubkeys.txt $MAX  --duration=$T --num_connections=$C  --latency=$1  --tx-size $TX_SIZE --num_clients $N --disable_congestion
./plot_timelapse_data.py solana_pubkeys.txt

