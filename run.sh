T='sudo ./main.py solana_pubkeys.txt  --duration=3.0'
N=5
rm -f datapoints.csv
TX_SZ=176
./make_stakes.py --min-stake=0 --max-stake=0  $N
$T --latency=5 --tx-size $TX_SZ
$T --latency=50 --tx-size $TX_SZ
$T --latency=100 --tx-size $TX_SZ
$T --latency=150 --tx-size $TX_SZ
$T --latency=200 --tx-size $TX_SZ
./make_stakes.py --min-stake=10000 --max-stake=10000 $N
$T --latency=5 --tx-size $TX_SZ
$T --latency=50 --tx-size $TX_SZ
$T --latency=100 --tx-size $TX_SZ
$T --latency=150 --tx-size $TX_SZ
$T --latency=200 --tx-size $TX_SZ
python plot.py $TX_SZ bytes
rm -f datapoints.csv

TX_SZ=1024
./make_stakes.py --min-stake=0 --max-stake=0 $N
$T --latency=5 --tx-size $TX_SZ
$T --latency=50 --tx-size $TX_SZ
$T --latency=100 --tx-size $TX_SZ
$T --latency=150 --tx-size $TX_SZ
$T --latency=200 --tx-size $TX_SZ
./make_stakes.py --min-stake=10000 --max-stake=10000 $N
$T --latency=5 --tx-size $TX_SZ
$T --latency=50 --tx-size $TX_SZ
$T --latency=100 --tx-size $TX_SZ
$T --latency=150 --tx-size $TX_SZ
$T --latency=200 --tx-size $TX_SZ
python plot.py $TX_SZ bytes
rm -f datapoints.csv
