# MiniMart Kubernetes Learning Lab

A fully functional, containerised e-commerce application built specifically to teach Kubernetes concepts through hands-on experience.

---

## What You'll Learn

| Concept | Where |
|---|---|
| Pod identity & ephemeralness | Every API response includes the Pod name |
| Service types (NodePort vs ClusterIP) | Frontend (NodePort) + Backend (ClusterIP) |
| DNS-based service discovery | Frontend uses `minimart-backend-svc` hostname |
| Load balancing across replicas | Refresh the shop — different Pods respond |
| Deployments & ReplicaSets | Self-healing experiment in the Lab |
| Rolling updates | `kubectl rollout` commands |
| Liveness & Readiness probes | Health check experiment in the Lab |
| Resource requests & limits | Defined in every Deployment |
| Downward API | Pod name injected via env vars |

---

## Project Structure

```
kubernetes_project/
├── backend/
│   ├── app.py              ← Flask API (products, health, pod identity)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py              ← Flask proxy + page server
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html      ← Shop page
│   │   └── lab.html        ← K8s Lab Dashboard
│   └── static/
│       ├── style.css
│       ├── lab.css
│       ├── shop.js
│       └── lab.js
├── k8s/
│   ├── backend-deployment.yaml   ← Backend Deployment + ClusterIP Service
│   ├── frontend-deployment.yaml  ← Frontend Deployment + NodePort Service
│   └── loadbalancer-service.yaml ← Optional LoadBalancer Service
└── deploy.ps1              ← One-command Windows deploy script
```

---

## Prerequisites

- Windows 11
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Hyper-V or WSL2 backend)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)

Verify your setup:
```powershell
docker --version
minikube version
kubectl version --client
```

---

## Quick Start (Windows PowerShell)

```powershell
# 1. Clone / navigate to the project
cd e:\kubernetes_project

# 2. Run the deploy script (builds images, applies manifests, waits for pods)
.\deploy.ps1

# 3. Open in your browser
#    URL is printed at the end of the script, typically:
#    http://192.168.49.2:30080      ← Shop
#    http://192.168.49.2:30080/lab  ← K8s Lab Dashboard
```

> **Important – image build order matters.**
> The script runs `minikube docker-env` first so Docker builds the image
> *inside* Minikube's daemon (not your host Docker). This is why
> `imagePullPolicy: Never` works.

---

## Manual Step-by-Step

```powershell
# Start Minikube
minikube start --driver=docker --cpus=2 --memory=3g

# Point shell at Minikube's Docker
& minikube -p minikube docker-env --shell powershell | Invoke-Expression

# Build images
docker build -t minimart-backend:latest  ./backend
docker build -t minimart-frontend:latest ./frontend

# Deploy
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Wait
kubectl rollout status deployment/minimart-backend
kubectl rollout status deployment/minimart-frontend

# Access
minikube service minimart-frontend-svc --url
```

---

## K8s Lab Experiments

Navigate to `/lab` in your browser for the interactive dashboard.

### A – Request Routing
```powershell
# Watch which pod handles each request
for ($i=1; $i -le 10; $i++) {
  $r = Invoke-WebRequest -Uri "http://$(minikube ip):30080/api/proxy/info" -UseBasicParsing
  ($r.Content | ConvertFrom-Json).frontend_pod
}
```

### B – Scaling
```powershell
kubectl scale deployment minimart-frontend --replicas=5
kubectl get pods -l app=minimart-frontend -w
kubectl scale deployment minimart-frontend --replicas=3
```

### C – Self-Healing
```powershell
# Get a pod name
kubectl get pods -l app=minimart-frontend

# Delete it (Kubernetes will recreate it)
kubectl delete pod <pod-name>

# Watch the replacement appear
kubectl get pods -l app=minimart-frontend -w
```

### D – Inspect Service Endpoints
```powershell
# See actual pod IPs behind the ClusterIP Service
kubectl get endpoints minimart-backend-svc
kubectl get endpoints minimart-frontend-svc
```

### E – Health Probes
```powershell
# See probe configuration
kubectl describe pod -l app=minimart-backend | Select-String -Pattern "Liveness|Readiness" -Context 0,5

# Hit probes directly (via port-forward)
kubectl port-forward svc/minimart-backend-svc 5000:5000 &
curl http://localhost:5000/health
curl http://localhost:5000/ready
```

---

## Rolling Update Demo

```powershell
# Update the backend version label (triggers a rolling update)
kubectl set env deployment/minimart-backend APP_VERSION=2.0.0

# Watch pods roll
kubectl rollout status deployment/minimart-backend

# Undo
kubectl rollout undo deployment/minimart-backend
```

---

## LoadBalancer Demo (Optional)

```powershell
kubectl apply -f k8s/loadbalancer-service.yaml

# In a separate terminal (requires admin / elevated prompt)
minikube tunnel

# Get the external IP
kubectl get svc minimart-frontend-lb
# Open http://<EXTERNAL-IP>:8080
```

---

## Teardown

```powershell
# Remove deployments/services only
kubectl delete -f k8s/

# Or completely delete the cluster
.\deploy.ps1 -Clean
```

---

## Architecture Overview

```
Browser
  │
  │  HTTP :30080
  ▼
NodePort Service (minimart-frontend-svc)
  │
  │  kube-proxy → random pod selection
  ├──► Frontend Pod 1 (minimart-frontend-xxx)
  ├──► Frontend Pod 2 (minimart-frontend-yyy)
  └──► Frontend Pod 3 (minimart-frontend-zzz)
            │
            │  HTTP → minimart-backend-svc:5000 (Kubernetes DNS)
            ▼
        ClusterIP Service (minimart-backend-svc)
            │
            ├──► Backend Pod 1 (minimart-backend-aaa)
            └──► Backend Pod 2 (minimart-backend-bbb)
                        │
                        │  in-memory data (resets on Pod restart)
                        └──► Product Data [ ]
```

---

## Design Decisions for Students

| Decision | Why |
|---|---|
| `imagePullPolicy: Never` | Avoids needing a container registry for local labs |
| ClusterIP for backend | Backend never needs direct browser access — teaches proper isolation |
| NodePort (not LoadBalancer) | Works without `minikube tunnel`; simpler for first labs |
| Downward API for pod name | Teaches a real K8s pattern, not a hack |
| In-memory data | Forces students to think about persistence (Exercise 2: add PostgreSQL) |
| Proxy pattern in frontend | Mirrors real microservice architecture; avoids CORS and cluster exposure |
