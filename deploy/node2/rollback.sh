#!/bin/sh
# Remove node-2 completely: node object, node password, container, volumes,
# firewall rules and files. Safe to run more than once.
# Usage (in /opt/aiops-node2):  sudo ./rollback.sh
set -u
echo "removing node-2"
kubectl drain node-2 --ignore-daemonsets --delete-emptydir-data --force --timeout=60s 2>/dev/null || true
kubectl delete node node-2 --ignore-not-found
# Without this, the server rejects a future node-2 ("Node password rejected").
kubectl -n kube-system delete secret node-2.node-password.k3s --ignore-not-found
docker compose -f /opt/aiops-node2/compose.yaml down -v 2>/dev/null || true
ufw delete allow from 172.31.250.0/24 to any port 6443 proto tcp 2>/dev/null || true
ufw delete allow from 172.31.250.0/24 to any port 8472 proto udp 2>/dev/null || true
echo "node-2 removed. Delete /opt/aiops-node2 when you no longer need the files."
