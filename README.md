# prep
make a symlink "server" that points to streamer's swqos example binary
`cd mock_server && cargo build --release`  
`./make_stakes.py` to produce stake identities

# simulation
`RUST_LOG="solana_streamer=debug" ./main.py solana_pubkeys.txt 0`

