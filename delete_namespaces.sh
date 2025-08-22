#!/bin/bash
echo "Deleting all network namespaces..."
for ns in $(ip netns list | awk '{print $1}'); do
    echo "Deleting namespace: $ns"
    ip netns del "$ns"
done
echo "All namespaces deleted"
echo "Killing clients and server"
killall client
killall server
