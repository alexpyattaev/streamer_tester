## Mock agave client

The`solana_mock_client` demonstrates how agave client works with quic-based TPU protocol.


In a new terminal execute:

```shell
$ ./solana_mock_client --target <IP>:8009 --duration 600 --num-connections 4
```

Note that we don't use blockhash. This would require usage of RPC client.



## Some notes

Currently, what I found that we set one timeout of all and not `keep_alive_interval`

* Methods calling `handle_connection` do quite some locking to update connection cache, what is the impact of this on performance?
* In `handle_connection` variable `let mut maybe_batch = None;` should not exist, it should be part of the `hand_chunk`. Also error should be  handled on the level where it is received.
* Do we really need to handle chunks manually using packet accumulator?
* in `handle_connection` the `stream_exit` is set to true when ConnectionEntry is dropped. Is it a good pattern with tokio? or maybe there is a nicer way for the same.
