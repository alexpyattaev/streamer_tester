import numpy as np

server_record_dtype = np.dtype(
    [
        ("id", "S32"),  # 32-byte pubkey
        ("size", np.uint64),
        ("time", np.uint64),
    ]
)

server_local_dtype = np.dtype(
    [
        ("id", "S32"),  # 32-byte pubkey
        ("size", np.uint64),
        ("time", np.float64),
    ]
)

client_record_dtype = np.dtype(
    [
        ("udp_tx", np.uint64),
        ("udp_rx", np.uint64),
        ("sent", np.uint64),
        ("congestion_events", np.uint64),
        ("congestion_window", np.uint64),
        ("lost_packets", np.uint64),
        ("time", np.uint64),
        ("connection_id", np.uint64),
    ]
)
client_local_dtype = np.dtype(
    [
        ("udp_tx", np.uint64),
        ("udp_rx", np.uint64),
        ("sent", np.uint64),
        ("congestion_events", np.uint64),
        ("congestion_window", np.uint64),
        ("lost_packets", np.uint64),
        ("time", np.float64),
        ("connection_id", np.uint64),
    ]
)
