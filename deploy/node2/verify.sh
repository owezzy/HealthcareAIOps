#!/bin/sh
# Prove node-2 works, then (with --promote) remove its canary taint so the
# simulated estate can schedule there. Without --promote it only checks.
# Usage (in /opt/aiops-node2):  sudo ./verify.sh [--promote]
set -u
fail=0
ok()   { printf '  ok    %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }
TOLERATE_ALL='[{"key":"aiops.io/estate","operator":"Exists"},{"key":"aiops.io/canary","operator":"Exists"}]'

echo "node-2 verification"

if kubectl wait --for=condition=Ready node/node-2 --timeout=180s >/dev/null 2>&1; then
    ok "node-2 is Ready"
else
    bad "node-2 not Ready after 3 minutes; see: docker logs aiops-node-2 | tail -50"
    exit 1
fi

taints=$(kubectl get node node-2 -o jsonpath='{range .spec.taints[*]}{.key}={.value}:{.effect} {end}')
echo "$taints" | grep -q 'aiops.io/estate=only:NoSchedule' && ok "estate-only taint present" \
    || bad "estate-only taint missing"

# A pod without tolerations must not land on node-2.
kubectl run node2-taint-check --image=busybox:1.37 --restart=Never \
    --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"node-2"}}}' -- true >/dev/null
sleep 10
phase=$(kubectl get pod node2-taint-check -o jsonpath='{.status.phase}')
[ "$phase" = "Pending" ] && ok "untolerated pod stays Pending" || bad "untolerated pod is $phase"
kubectl delete pod node2-taint-check --wait=false >/dev/null

# Cross-node path: a pod on node-2 resolves through CoreDNS, which runs on the host node.
kubectl run node2-net-check --image=busybox:1.37 --restart=Never \
    --overrides="{\"spec\":{\"nodeSelector\":{\"kubernetes.io/hostname\":\"node-2\"},\"tolerations\":$TOLERATE_ALL}}" \
    -- nslookup kubernetes.default.svc.cluster.local >/dev/null
if kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/node2-net-check --timeout=120s >/dev/null 2>&1; then
    ok "pod on node-2 reached CoreDNS on the host node (VXLAN works)"
else
    bad "cross-node DNS failed; check the 8472/udp rule. Logs: kubectl logs node2-net-check"
fi
kubectl delete pod node2-net-check --wait=false >/dev/null

available=$(free -m | awk '/^Mem:/ {print $7}')
[ "$available" -ge 600 ] && ok "host still has ${available} MiB available" \
    || bad "host down to ${available} MiB available"

if [ "$fail" -ne 0 ]; then
    echo "verification FAILED: node-2 keeps its canary taint. Fix, or run rollback.sh"
    exit 1
fi
echo "verification passed"
if [ "${1:-}" = "--promote" ]; then
    kubectl taint node node-2 aiops.io/canary=true:NoExecute- >/dev/null && ok "canary taint removed: node-2 is open to the estate"
else
    echo "run again with --promote to open node-2 to the estate"
fi
