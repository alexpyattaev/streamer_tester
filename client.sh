TARGET=$1 #namespace name suffix
TARGET_IP=$2 #namespace IP
DELAY_MS=$3 #namespace link delay to server connection
DELAY_DISTRIBUTION_MS=$4 #namespace link delay distribution to server connection
CLI="ip netns exec client${TARGET}"
LOSS_PERCENT=$5 #namespace link loss percentage to server connection
SRV="ip netns exec server"

echo "Creating a namespace client ${TARGET}"
ip netns del client${TARGET}
ip netns add client${TARGET}

echo "Set up link between client${TARGET} and server namespaces"
ip link add veth_srv-${TARGET} type veth peer name veth-${TARGET}
ip link set dev veth-${TARGET} netns client${TARGET}
ip link set dev veth_srv-${TARGET} netns server
$SRV ip link set veth_srv-${TARGET} master srv-br
$SRV ip link set veth_srv-${TARGET} up
$CLI ip a a 10.0.1.${TARGET_IP}/24 dev veth-${TARGET}
$CLI ip link set veth-${TARGET} up
echo "Connectivity check"
$CLI ping 10.0.1.1 -c 1 -W 0.00001 >> /dev/null  || echo"ping test fail"
echo "OK"
echo "Set host ${TARGET} link quality"
echo "Set delay of ${DELAY_MS}ms, packet loss ${LOSS_PERCENT}%"
$SRV tc qdisc add dev veth_srv-${TARGET} root handle 1: netem delay ${DELAY_MS}ms ${DELAY_DISTRIBUTION_MS}ms distribution normal
$SRV tc qdisc add dev veth_srv-${TARGET} parent 1: handle 2: netem loss ${LOSS_PERCENT}

$CLI tc qdisc add dev veth-${TARGET} root handle 1: netem delay ${DELAY_MS}ms ${DELAY_DISTRIBUTION_MS}ms distribution normal
$CLI tc qdisc add dev veth-${TARGET} parent 1: handle 2: netem loss ${LOSS_PERCENT} rate 100Mbit corrupt 1% duplicate 1%
echo "Run 'ip netns exec client $TARGET bash' to start a shell in namespace for accessing client-$TARGET"
