#!/bin/bash
SRV="ip netns exec server"

echo "Creating a directory for result"
mkdir -p results
chmod 666 results

echo "Add namespace"
ip netns del server 2>> /dev/null
ip netns add server


echo "Configuring server connection interfaces"
$SRV ip link add srv-br type bridge
$SRV ip l set srv-br up
$SRV ip a a 10.0.1.1/24 dev srv-br



echo 'Run "ip netns exec server bash" to start a shell in namespace for SERVER'
#echo 'Internet access is not configured inside the namespaces.'
