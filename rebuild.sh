set -ex
cd ~/agave/streamer 
cargo build --release --examples
cd ~/streamer_torture/mock_server
cargo build --release
cd ../
TX_SIZE=1000
N=24
C=4
#export RUST_LOG="info,solana_streamer=debug"
sudo --preserve-env=RUST_LOG  ./main.py solana_pubkeys.txt  --duration=2.0 --num_connections=$C  --latency=$1  --tx-size $TX_SIZE --num_clients $N
./plot_timelapse_data.py 

