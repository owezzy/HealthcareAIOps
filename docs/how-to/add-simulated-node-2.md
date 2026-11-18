# Add the simulated node-2

This guide adds `node-2`, a K3s worker that runs as a Docker container on `owezzy-db` ([ADR-0013](../adr/0013-simulated-node-2.md)). It gives the cluster a second node for the simulated estate and a real node to fail in scenario S5, without a second VPS.

Run every command on `owezzy-db` as a user who can use `sudo`, `docker`, `ufw` and `kubectl`.

## Before you start

- K3s version on the server matches the image tag in `deploy/node2/compose.yaml`:

  ```bash
  kubectl get node owezzy-db -o jsonpath='{.status.nodeInfo.kubeletVersion}'   # v1.37.2+k3s1
  ```

- About 600 MiB of memory is free: `free -m` shows `available` above 1,100 (500 MiB is the host's eviction threshold).

## 1. Copy the files and set the join token

```bash
sudo mkdir -p /opt/aiops-node2
sudo cp deploy/node2/compose.yaml /opt/aiops-node2/
echo "K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/agent-token)" | sudo tee /opt/aiops-node2/node2.env >/dev/null
sudo chmod 600 /opt/aiops-node2/node2.env
```

The agent token lets a node join the cluster. Keep it out of git and out of logs.

## 2. Open the two ports to the node's subnet only

```bash
sudo ufw allow from 172.31.250.0/24 to any port 6443 proto tcp comment 'aiops node-2: K3s API'
sudo ufw allow from 172.31.250.0/24 to any port 8472 proto udp comment 'aiops node-2: flannel VXLAN'
```

Both rules accept traffic from the node's private Docker subnet only. Nothing new is opened to the internet.

## 3. Start the node

```bash
cd /opt/aiops-node2 && sudo docker compose up -d
```

## 4. Check it joined

```bash
kubectl get nodes -o wide                          # node-2 Ready within ~1 minute
kubectl describe node node-2 | grep -A2 Taints     # aiops.io/estate=only:NoSchedule
```

Prove the taint keeps everything else off. This pod stays `Pending`:

```bash
kubectl run taint-check --image=busybox --restart=Never --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"node-2"}}}' -- sleep 5
kubectl get pod taint-check     # Pending: untolerated taint
kubectl delete pod taint-check
```

Prove pod networking across the two nodes. Run a tolerating pod on node-2 and reach the cluster DNS:

```bash
kubectl run net-check --image=busybox --restart=Never \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"node-2"},"tolerations":[{"key":"aiops.io/estate","operator":"Equal","value":"only","effect":"NoSchedule"}]}}' \
  -- nslookup kubernetes.default.svc.cluster.local
kubectl logs net-check          # an answer from 10.43.0.10 means VXLAN works
kubectl delete pod net-check
```

## 5. Rehearse S5 by hand

```bash
sudo docker stop aiops-node-2
kubectl get node node-2 -w     # NotReady after about 40 s
sudo docker start aiops-node-2  # Ready again within a minute
```

The fault injector (week 2) does the same from inside the cluster with `SIGSTOP` and `SIGCONT`, as described in ADR-0013.

## If something fails

| Symptom | Likely cause | Check |
|---|---|---|
| Container restarts in a loop | cgroup v2 nesting | `sudo docker logs aiops-node-2 \| tail -50` |
| Node never appears | API port blocked or wrong token | Step 2 rules; `node2.env`; logs mention `401` or `connection refused` |
| Node `Ready` but `net-check` times out | VXLAN (8472/udp) blocked | Step 2 rule for 8472; `kubectl -n kube-system logs` for flannel errors |
| Host pods evicted | Not enough free memory | `free -m`; lower `mem_limit` or stop the node |

## Remove it

```bash
kubectl drain node-2 --ignore-daemonsets --delete-emptydir-data
kubectl delete node node-2
cd /opt/aiops-node2 && sudo docker compose down -v
sudo ufw delete allow from 172.31.250.0/24 to any port 6443 proto tcp
sudo ufw delete allow from 172.31.250.0/24 to any port 8472 proto udp
sudo rm -rf /opt/aiops-node2
```
