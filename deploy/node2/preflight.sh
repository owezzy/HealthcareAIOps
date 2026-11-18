#!/bin/sh
# Read-only checks before starting node-2 on owezzy-db. Changes nothing.
# Usage (in /opt/aiops-node2):  sudo ./preflight.sh
set -u
fail=0
ok()   { printf '  ok    %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }

echo "node-2 preflight"

image_tag=$(sed -n 's/^ *image: rancher\/k3s:\([^ ]*\).*/\1/p' compose.yaml)
server=$(kubectl get node owezzy-db -o jsonpath='{.status.nodeInfo.kubeletVersion}' | tr '+' '-')
[ "$server" = "$image_tag" ] && ok "K3s version $server matches the image" \
    || bad "server is $server but compose.yaml uses $image_tag"

available=$(free -m | awk '/^Mem:/ {print $7}')
[ "$available" -ge 1100 ] && ok "${available} MiB available (needs 1100: 512 cap + 500 eviction margin)" \
    || bad "only ${available} MiB available; the host kubelet evicts below 500 MiB"

[ "$(stat -fc %T /sys/fs/cgroup)" = "cgroup2fs" ] && ok "cgroup v2" || bad "not cgroup v2"
for module in overlay br_netfilter vxlan; do
    lsmod | grep -qw "^$module" && ok "kernel module $module loaded" || bad "kernel module $module not loaded"
done

kubectl get node node-2 >/dev/null 2>&1 && bad "a node named node-2 already exists (run rollback.sh)" \
    || ok "no existing node-2"
kubectl -n kube-system get secret node-2.node-password.k3s >/dev/null 2>&1 \
    && bad "leftover node password secret blocks the name (run rollback.sh)" || ok "no leftover node password"

if docker network inspect $(docker network ls -q) -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null \
    | grep -q '172\.31\.250\.'; then
    docker network inspect aiops-node2_node2 >/dev/null 2>&1 && ok "subnet 172.31.250.0/24 is ours" \
        || bad "subnet 172.31.250.0/24 is used by another Docker network"
else
    ok "subnet 172.31.250.0/24 is free"
fi

if [ -s node2.env ] && grep -q '^K3S_TOKEN=..*' node2.env; then
    [ "$(stat -c %a node2.env)" = "600" ] && ok "node2.env has a token and mode 600" \
        || bad "node2.env must be mode 600"
else
    bad "node2.env is missing or has no K3S_TOKEN"
fi

ufw status | grep -q '6443/tcp .*172.31.250.0/24' && ok "firewall allows the API port from the node subnet" \
    || bad "missing ufw rule: 6443/tcp from 172.31.250.0/24"
ufw status | grep -q '8472/udp .*172.31.250.0/24' && ok "firewall allows VXLAN from the node subnet" \
    || bad "missing ufw rule: 8472/udp from 172.31.250.0/24"

[ "$fail" -eq 0 ] && echo "preflight passed" || echo "preflight FAILED: fix the items above before starting node-2"
exit "$fail"
