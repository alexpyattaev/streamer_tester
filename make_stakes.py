#!/usr/bin/env python3
import subprocess
import random
import shutil
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(prog='make_stakes',description="Stake identity maker",
                                     )
parser.add_argument('hosts',type=int, default=5, help='how many to make')
parser.add_argument('--min-stake', type=int, default=10000, help='min stake in SOL')
parser.add_argument('--max-stake', type=int, default=10000, help='max stake in SOL')
args = parser.parse_args()
# --- Configuration ---

output_file = Path("solana_pubkeys.txt")
keypair_dir = Path("solana_keypairs")  # folder to store keypair JSON files
shutil.rmtree(keypair_dir)
keypair_dir.mkdir(exist_ok=True)

# --- Generate keypairs ---
pubkeys = []

for i in range(1, args.hosts + 1):
    keypair_path = keypair_dir / f"keypair_{i}.json"
    # Run solana-keygen to generate a new keypair
    result = subprocess.run(
        ["solana-keygen", "new", "--no-passphrase", "--outfile", str(keypair_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Parse public key from stdout
    # solana-keygen prints something like:
    #   Generating a new keypair
    #   Wrote new keypair to keypair_1.json
    #   pubkey: 3seYyr5hJ9JgCzJ2umYvEfpRbpykBiH7j7YDRUX3qJ7d
    for line in result.stdout.splitlines():
        if line.startswith("pubkey:"):
            pubkey = line.split("pubkey:")[1].strip()
            pubkeys.append(pubkey)
            break
    else:
        raise RuntimeError("keygen output parse fail")
    shutil.move(f"{keypair_dir}/keypair_{i}.json", f"{keypair_dir}/{pubkey}.json")

# --- Write public keys to file ---
with output_file.open("w") as f:
    for pk in pubkeys:
        stake = random.randint(args.min_stake, args.max_stake)
        f.write(f"{pk} {stake}\n")

print(f"Generated {args.hosts} keypairs. Public keys written to {output_file}")
