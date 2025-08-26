#!/bin/bash

set -xeuo pipefail

SRV="ip netns exec server"

echo "Creating a directory for result"
rm -rf results
mkdir -p results
chmod a+rwx results

echo "Add namespace"
set +e
ip netns del server 2>> /dev/null
set -e
ip netns add server


echo "Configuring server connection interfaces"
$SRV ip link add srv-br type bridge
$SRV ip l set srv-br up
$SRV ip a a 10.0.1.1/24 dev srv-br



echo 'Run "ip netns exec server bash" to start a shell in namespace for SERVER'
#echo 'Internet access is not configured inside the namespaces.'
