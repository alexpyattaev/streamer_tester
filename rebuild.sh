set -ex
cd ~/agave/streamer 
cargo build --release --examples
cd ~/streamer_torture/mock_server
cargo build --release
cd ../
TX_SIZE=1000
N=24
C=5
T=5.0
#export RUST_LOG="info,solana_streamer=debug"
sudo --preserve-env=RUST_LOG  ./main.py solana_pubkeys.txt --max-tps 100000  --duration=$T --num_connections=$C  --latency=$1  --tx-size $TX_SIZE --num_clients $N
./plot_timelapse_data.py 

