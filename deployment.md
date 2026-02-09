# Deployment Guide (GitLab CI → VM)

This project is designed to be deployed by **GitLab CI** onto a **Linux VM** that has a **GitLab Runner running on the VM** with access to the VM’s Docker daemon. The pipeline builds a Docker image, pushes it to the GitLab Container Registry, then the VM runner pulls and runs the containers.

If you don’t have VM access, coordinate with DevOps to set up the runner + required host paths and then you can deploy by pushing Git tags.

## 1) Prerequisites (DevOps)

### VM requirements
- Docker installed and running.
- The user that the GitLab Runner runs as can run Docker commands (`docker ps`, `docker pull`, `docker run`).
- Outbound network access from the VM to:
  - GitLab Container Registry (to pull images)
  - OpenAI API (and optionally Exa) from inside the container
- Inbound access to the app port (default `8000`) or an internal reverse-proxy routing to it.

### GitLab Runner requirements (important)
The deploy job executes `docker run ...` and must affect the **VM**. That means:
- Runner executor should be **Shell on the VM**, or
- Docker executor with host Docker socket bind (advanced), but **not** pure Docker-in-Docker where containers are isolated from the VM host.

The pipeline uses runner tag `ai-ticketing` (see `.gitlab-ci.yml`). If your runner uses a different tag, update `.gitlab-ci.yml`.

### Host persistence paths
The deployment uses these host paths (create once; ensure write permissions):
- App data: `/opt/docker-data/dash`
- Postgres data: `/opt/docker-data/dash-db`

These map into containers as:
- Dash data dir: `/data`
- Postgres data dir: `/var/lib/postgresql`

## 2) GitLab project setup (you)

### Enable Container Registry
In GitLab project settings, ensure the **Container Registry** is enabled.

### Add CI/CD variables
Add these variables in **Settings → CI/CD → Variables**:
- Required:
  - `OPENAI_API_KEY` (masked, protected as appropriate)
- Optional:
  - `EXA_API_KEY` (only if you want web research via Exa MCP)
- Database (only needed if you want non-default credentials):
  - `DB_USER` (default `ai`)
  - `DB_PASS` (default `ai`)
  - `DB_DATABASE` (default `ai`)

Notes:
- If you use “Protected variables”, deploy using “Protected tags” (per your GitLab policy).
- Do not store secrets in the repository.

## 3) What the pipeline does

The pipeline is defined in `.gitlab-ci.yml` and runs on **Git tags only**.

Stages:
1. **build**
   - Builds the Docker image from `Dockerfile`
   - Pushes:
     - `$CI_REGISTRY_IMAGE/dash:$CI_COMMIT_TAG`
     - `$CI_REGISTRY_IMAGE/dash:latest`
2. **deploy**
   - Creates Docker network `dash` (if missing)
   - Starts/refreshes a Postgres container `dash-db` (pgvector image)
   - Starts/refreshes the API container `dash-api`
3. **seed (manual)**
   - Optional job that loads sample F1 data + knowledge into the DB

## 4) How to deploy

1. Push code to GitLab.
2. Create and push a **Git tag**:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitLab will run the pipeline for that tag and deploy to the VM via the VM runner.

### Verify deployment
From a machine that can reach the VM:
- Swagger docs should be available at:
  - `http://<vm-host>:8000/docs`

DevOps can also verify on the VM:
```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker logs --tail=200 dash-api
docker logs --tail=200 dash-db
```

## 5) Optional: load sample data & knowledge (manual CI job)

The pipeline includes a manual job named `seed_prod` that runs:
- `python -m dash.scripts.load_data`
- `python -m dash.scripts.load_knowledge`

Run this once after first deploy if you want the **sample F1 dataset** and knowledge preloaded.

If you’re deploying Dash for a real dataset, you’ll likely skip this and instead load your own schema/knowledge.

## 6) Using an external Postgres instead of the bundled container

By default, the pipeline runs `dash-db` on the VM.

If DevOps already provides Postgres:
- Remove (or disable) the `dash-db` `docker run` block in `deploy_prod` in `.gitlab-ci.yml`.
- Set these CI/CD variables (or hardcode them in the job):
  - `DB_HOST` (hostname)
  - `DB_PORT` (usually `5432`)
  - `DB_USER`, `DB_PASS`, `DB_DATABASE`
- Update the `dash-api` `docker run` to use `DB_HOST="$DB_HOST"` instead of `DB_HOST="dash-db"`.

## 7) Rollback strategy

Deployments are tag-based, so rollback is simply deploying an older tag:
```bash
git tag v0.0.9
git push origin v0.0.9
```

Alternatively, DevOps can run the previous image tag directly:
```bash
docker pull <registry>/<path>/dash:<older-tag>
docker stop dash-api && docker rm dash-api
docker run ... <registry>/<path>/dash:<older-tag> ...
```

## 8) Troubleshooting

### Pipeline fails at `docker login` / `docker push`
- Confirm Container Registry is enabled.
- Confirm the runner has network access to GitLab registry.
- Confirm the job is running on the correct runner with Docker available.

### Deploy job “succeeds” but nothing changes on the VM
- Runner is not on the VM (common). Ensure VM runner is used (tags match).
- Runner is Docker-in-Docker and not controlling the host daemon.

### `dash-api` exits immediately
- Check logs: `docker logs --tail=200 dash-api`
- Common causes:
  - Missing `OPENAI_API_KEY`
  - DB connectivity issues (wrong host/port/credentials)
  - Port conflicts (something already binds `8000`)

### DB container keeps restarting
- Check logs: `docker logs --tail=200 dash-db`
- Ensure `/opt/docker-data/dash-db` exists and is writable.

## 9) Security notes

- Treat `OPENAI_API_KEY` (and any DB credentials) as secrets: masked + protected variables.
- Prefer running Dash behind a reverse proxy with TLS (Nginx/Traefik) rather than exposing `8000` directly to the internet.
- Restrict inbound traffic to the smallest set of source IPs possible.

