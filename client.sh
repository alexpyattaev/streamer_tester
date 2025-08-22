TARGET=$1 # namespace name suffix
TARGET_IP=$2 # host IP last digit
DELAY_MS=$3 # link delay to server
DELAY_DISTRIBUTION_MS=$4 #namespace link delay distribution to server
CLI="ip netns exec client${TARGET}"
LOSS_PERCENT=$5 # link loss percentage to server
SRV="ip netns exec server"

echo "Creating a namespace client${TARGET}"
ip netns del client${TARGET} 2>>/dev/null
ip netns add client${TARGET}

echo "Set up link between client${TARGET} and server namespaces"
ip link add veth_srv-${TARGET_IP} type veth peer name veth-${TARGET_IP}
ip link set dev veth-${TARGET_IP} netns client${TARGET}
ip link set dev veth_srv-${TARGET_IP} netns server
$SRV ip link set veth_srv-${TARGET_IP} master srv-br
$SRV ip link set veth_srv-${TARGET_IP} up
$CLI ip a a 10.0.1.${TARGET_IP}/24 dev veth-${TARGET_IP}
$CLI ip link set veth-${TARGET_IP} up
echo "Connectivity check"
$CLI ping 10.0.1.1 -c 1 -W 0.00001 >> /dev/null  || exit 1
echo "OK"
echo "Set host ${TARGET} link quality"
echo "Set delay of ${DELAY_MS}ms, packet loss ${LOSS_PERCENT}%"
$SRV tc qdisc add dev veth_srv-${TARGET_IP} root handle 1: netem delay ${DELAY_MS}ms ${DELAY_DISTRIBUTION_MS}ms distribution normal
$SRV tc qdisc add dev veth_srv-${TARGET_IP} parent 1: handle 2: netem loss ${LOSS_PERCENT}

$CLI tc qdisc add dev veth-${TARGET_IP} root handle 1: netem delay ${DELAY_MS}ms ${DELAY_DISTRIBUTION_MS}ms distribution normal
$CLI tc qdisc add dev veth-${TARGET_IP} parent 1: handle 2: netem loss ${LOSS_PERCENT} rate 100Mbit corrupt 1% duplicate 1%
echo "Run 'ip netns exec client${TARGET} bash' to start a shell in namespace for accessing client $TARGET"
