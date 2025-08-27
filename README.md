# prep

sudo apt install openvswitch-common openvswitch-switch openvswitch-testcontroller python3-openvswitch                                                                           
sudo apt install at  mininet python3-numpy


`git clone  https://github.com/alexpyattaev/agave/tree/streamer_tests_binding`
cd streamer
cargo build --release --examples (builds the swqos binary)

make a symlink "server" that points to streamer's swqos example binary
`cd mock_server && cargo build --release`  
`./make_stakes.py 5` to produce stake identities

# simulation

`RUST_LOG="solana_streamer=debug" sudo --preserve-env=RUST_LOG ./main.py solana_pubkeys.txt --latency 10`

