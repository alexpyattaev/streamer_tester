# prep

Step 1: Install dependencies
`sudo apt install openvswitch-common openvswitch-switch openvswitch-testcontroller python3-openvswitch`
`sudo apt install at  mininet python3-numpy`

Step 2: Build SQWOS(Stake-weighted Quality of Service):
`git clone  https://github.com/anza-xyz/agave`
`cd agave/streamer && cargo build --release --examples` (builds the swqos binary)

Step 3: Make a symlink "server" that points to streamer's swqos example binary:
`ln -s agave/target/release/examples/swqos`

Step 4: Build other parts of test bed:
`cd mock_server && cargo build --release`

# simulation

`./make_stakes.py 5` to produce stake identities
`RUST_LOG="solana_streamer=debug" sudo --preserve-env=RUST_LOG ./main.py solana_pubkeys.txt --latency 10`
or
`sudo ./main.py solana_pubkeys.txt [args]` - no debug info
