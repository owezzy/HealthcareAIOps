# Deploy to owezzy-db

This guide deploys the app tier to the `owezzy-db` K3s node and publishes it at `https://aiops.owenadirah.com`. It follows [ADR-0012](../adr/0012-hosting-on-owezzy-db.md) (hosting) and [ADR-0009](../adr/0009-deployment-mechanism.md) (Flux from release tags).

You do the one-off setup (steps 1–6) once. After that, every deployment is a release: see [Cut a release](cut-a-release.md).

## Before you start

- You can run `kubectl` against the cluster (on the node, or with its kubeconfig).
- You can manage the `owenadirah.com` zone in Cloudflare (Zero Trust → Networks → Tunnels).
- You can change the visibility of the GitHub repository and its GHCR packages.

## 1. Create the database and role

The app uses the cluster's shared Postgres in namespace `postgres`. Create a dedicated role and database, and enable pgvector:

```bash
PASSWORD=$(openssl rand -hex 24)   # keep this for step 2

kubectl -n postgres exec -i postgres-0 -- psql -U postgres <<SQL
CREATE ROLE aiops LOGIN PASSWORD '${PASSWORD}';
CREATE DATABASE aiops OWNER aiops;
\c aiops
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

Result: `CREATE ROLE`, `CREATE DATABASE`, `CREATE EXTENSION`.

## 2. Create the namespace and secrets

Secrets are created on the cluster. They are never committed.

```bash
kubectl create namespace aiops-app

kubectl -n aiops-app create secret generic aiops-secrets \
  --from-literal=AIOPS_DATABASE_URL="postgresql+psycopg://aiops:${PASSWORD}@postgres.postgres.svc.cluster.local:5432/aiops" \
  --from-literal=AIOPS_INTERNAL_TOKEN="$(openssl rand -hex 32)"
```

The API runs its Alembic migrations in an init container on start, so you do not migrate by hand.

**Optional: a real model.** Without this secret the agent runs the keyless `fake:echo` model. To use a provider, create `aiops-llm` with the model and its key, then restart the agent:

```bash
kubectl -n aiops-app create secret generic aiops-llm \
  --from-literal=AIOPS_LLM_MODEL='openai:<model id>' \
  --from-literal=OPENAI_API_KEY='<key>'
kubectl -n aiops-app rollout restart deployment/agent
```

## 3. Create the Cloudflare tunnel

1. In Cloudflare Zero Trust, create a tunnel named `healthcare-aiops` (connector type: cloudflared). Copy its token.
2. Add a public hostname: `aiops.owenadirah.com` → service `http://web.aiops-app.svc.cluster.local:8080`.
3. Store the token on the cluster:

```bash
kubectl -n aiops-app create secret generic cloudflared-token --from-literal=token='<tunnel token>'
```

Only the web service is published. Its nginx routes `/api/copilotkit` to the runtime and `/api` to the API. The API's `/internal/*` routes are not reachable from outside.

## 4. Let the cluster read the code and images

Flux needs to read the repository, and the kubelet needs to pull the images from GHCR. Choose **one**:

- **Public:** make the repository and the four `healthcare-aiops-*` GHCR packages public. Nothing else to do.
- **Private:** add a read-only deploy key as secret `healthcare-aiops-git` in `flux-system` and uncomment `secretRef` in `deploy/flux/healthcare-aiops.yaml`. Create a GHCR pull secret in `aiops-app` and add it as `imagePullSecrets` to the four Deployments in an overlay patch.

## 5. Connect Flux

```bash
kubectl apply -f deploy/flux/healthcare-aiops.yaml
```

Flux now watches for release tags `v0.1.0` and later. Until the first release exists, it reports that no matching tag was found. That is expected.

## 6. Release

[Cut a release](cut-a-release.md). The tag triggers the image build, and Flux applies `deploy/overlays/demo` with the new image tags.

## 7. Check the deployment

```bash
kubectl -n flux-system get kustomization healthcare-aiops   # READY True, revision v0.1.0
kubectl -n aiops-app get pods                                # all Running and Ready
curl -s https://aiops.owenadirah.com/api/budget/today        # JSON with "state"
```

Then open `https://aiops.owenadirah.com/spike/assistant` and send a message.

## If something fails

| Symptom | Likely cause | Check |
|---|---|---|
| `api` stuck in `Init` | Migration cannot reach the database | `kubectl -n aiops-app logs deploy/api -c migrate`; check `AIOPS_DATABASE_URL` |
| `ImagePullBackOff` | Images private or tag not built | Step 4; the Images workflow run for the tag |
| Tunnel shows "inactive" | Token secret wrong or missing | `kubectl -n aiops-app logs deploy/cloudflared` |
| Budget meter reads "unknown" | API not ready, or an unpriced model was used | `kubectl -n aiops-app get pods`; `config/model-prices.yaml` |
