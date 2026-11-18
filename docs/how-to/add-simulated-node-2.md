# Add the simulated node-2

This guide adds `node-2`, a K3s worker that runs as a Docker container on `owezzy-db` ([ADR-0013](../adr/0013-simulated-node-2.md)). It gives the cluster a second node for the simulated estate and a real node to fail in scenario S5, without a second VPS.

The node joins as a **canary**: a `NoExecute` taint keeps every workload off it until `verify.sh` has proved it works. Any failure leaves production untouched, and `rollback.sh` removes everything.

Run every command on `owezzy-db` with `sudo` available.

## 1. Copy the files and set the join token

```bash
sudo mkdir -p /opt/aiops-node2
sudo cp deploy/node2/{compose.yaml,entrypoint.sh,resolv.conf,preflight.sh,verify.sh,rollback.sh} /opt/aiops-node2/
cd /opt/aiops-node2
echo "K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/agent-token)" | sudo tee node2.env >/dev/null
sudo chmod 600 node2.env
```

The agent token lets a node join the cluster. Keep it out of git and out of logs.

## 2. Open two ports to the node's subnet only

```bash
sudo ufw allow from 172.31.250.0/24 to any port 6443 proto tcp comment 'aiops node-2: K3s API'
sudo ufw allow from 172.31.250.0/24 to any port 8472 proto udp comment 'aiops node-2: flannel VXLAN'
```

Both rules accept traffic from the node's private Docker subnet only. Nothing new is opened to the internet.

## 3. Run the preflight

```bash
sudo ./preflight.sh
```

It changes nothing. It checks the K3s version against the image, free memory, cgroup v2, kernel modules, leftovers from an earlier node-2, the subnet, the token file and the firewall rules. Fix every `FAIL` before you continue.

## 4. Start the node

```bash
sudo docker compose up -d
```

## 5. Verify, then open it to the estate

```bash
sudo ./verify.sh            # checks only
sudo ./verify.sh --promote  # checks, then removes the canary taint
```

`verify.sh` proves four things:

1. The node becomes `Ready`.
2. The estate-only taint is present.
3. A pod with no tolerations stays `Pending`.
4. A pod on node-2 reaches CoreDNS on the host node, which proves cross-node networking (VXLAN).

It also re-checks host memory. If anything fails, the canary taint stays and nothing runs on node-2.

## 6. Rehearse S5 by hand

```bash
sudo docker stop aiops-node-2
kubectl get node node-2 -w      # NotReady after about 50 s (measured: 49 s)
sudo docker start aiops-node-2  # Ready again within seconds (measured: 5 s)
```

The fault injector (week 2) does the same from inside the cluster with `SIGSTOP` and `SIGCONT`, as described in ADR-0013.

## If something fails

| Symptom | Likely cause | What to do |
|---|---|---|
| Container restarts in a loop, logs mention cgroups or `EBUSY` | cgroup v2 preparation did not run | Check that `entrypoint.sh` is mounted and executable; `sudo docker logs aiops-node-2 \| tail -50` |
| `Node password rejected` | An earlier node-2 left its password secret | `sudo ./rollback.sh`, then start again from step 3 |
| Node never appears | API port blocked or wrong token | Step 2 rules; `node2.env`; logs mention `401` or `connection refused` |
| `Ready`, but the cross-node DNS check fails | VXLAN (8472/udp) blocked | Step 2 rule for 8472 |
| Host memory drops below 600 MiB | Too much on the host | `sudo ./rollback.sh`; revisit the estate size |

## Remove it

```bash
sudo ./rollback.sh && sudo rm -rf /opt/aiops-node2
```

It drains and deletes the node, deletes its password secret (otherwise a future node-2 is rejected), removes the container and its volumes, and deletes both firewall rules. It is safe to run twice.
