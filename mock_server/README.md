## Mock agave client and server

The `server` and `client` demonstrate how agave client/server works with quic-based TPU protocol.

1. Server (`server.rs`)

To model current server with relevant parameters:

```shell
$ RUST_LOG=info ./server --listen 0.0.0.0:8009 --receive-window-size 630784  --max-concurrent-streams 512 --stream-receive-window-size 1232
```

Server has an option to write reorder log in the csv file (see `--write_reordering_log`).

2. Client (`client.rs`)

In a new terminal execute:

```shell
$ ./client --target <IP>:8009 --duration 600 --num-connections 4
```

Note that we don't use blockhash. This would require usage of RPC client.


## What to change in the original client

* There is no need to `Arc` structures (connection etc) which are clonable already.
* We use QUIC_CONNECTION_HANDSHAKE_TIMEOUT which should not be used, max_idle_timeout will determine timeout.
* PORT 0 means that it will identified by OS so why do we search manually?
* Do we want to keep alive staked connections? It is possible to achieve by setting:

```rust
transport_config.max_idle_timeout(Some(timeout));
transport_config.keep_alive_interval(Some(QUIC_KEEP_ALIVE));
```

Currently, what I found that we set one timeout of all and not `keep_alive_interval`

* Methods calling `handle_connection` do quite some locking to update connection cache, what is the impact of this on performance?
* In `handle_connection` variable `let mut maybe_batch = None;` should not exist, it should be part of the `hand_chunk`. Also error should be  handled on the level where it is received.
* Do we really need to handle chunks manually using packet accumulator?
* in `handle_connection` the `stream_exit` is set to true when ConnectionEntry is dropped. Is it a good pattern with tokio? or maybe there is a nicer way for the same.
