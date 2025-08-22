#!/usr/bin/python
import numpy as np
import matplotlib.pyplot as plt
from base58 import b58encode, b58decode

record_dtype = np.dtype([
    ("id",  "S32"),   # 32-byte pubkey
    ("size", np.uint64),
    ("time", np.uint32),
])

data = np.fromfile("results/serverlog.bin", dtype=record_dtype)
stakes = [ l.split(' ') for l in open("solana_pubkeys.txt").readlines()]
stakes = {b58decode(a):b for a,b in stakes}


print(f"Captured {len(data)} transactions")
for id in stakes:
    print(f"{b58encode(id).decode('ascii')} = {(data['id'] == id).sum()}")
