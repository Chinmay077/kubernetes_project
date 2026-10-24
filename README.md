# MiniMart Kubernetes Learning Lab

A fully functional, containerised e-commerce microservices application built specifically to teach Kubernetes and modern Microservice concepts through interactive hands-on experiments.

---

## What You'll Learn

| Concept | Where & How It's Demonstrated |
|---|---|
| **Pod identity & ephemeralness** | Every API response includes the exact responding Pod name & host IP |
| **Service types (NodePort vs ClusterIP)** | Frontend (`NodePort 30080`), Backend & Notification (`ClusterIP` internal only) |
| **DNS-based service discovery** | Frontend resolves `minimart-backend-svc` and `minimart-notification-svc` by K8s DNS |
| **Load balancing across replicas** | Refresh the shop / lab — kube-proxy distributes requests across pods |
| **Deployments & ReplicaSets** | Self-healing experiment in the Lab (auto-healing terminated pods) |
| **Database Persistence (SQLite)** | Backend uses SQLite database with persistent volume mounts |
| **Async Microservice Messaging** | Backend fires async events to decoupled `notification-service` on CRUD |
| **Microservice Protocols Comparison** | Interactive comparison of REST, gRPC, WebSockets, & Event Brokers |
| **Rolling updates** | Zero-downtime updates via `kubectl rollout` |
| **Liveness & Readiness probes** | Probes ensure traffic is only routed to healthy containers |
| **Resource requests & limits** | Defined in every Deployment to prevent noisy-neighbor issues |
| **Downward API** | Pod metadata (pod name, IP, node name) injected directly via environment variables |

---

## Project Structure

```
kubernetes_project/
├── backend/
│   ├── app.py                      ← Flask API (SQLite DB, products CRUD, async event emitter)
│   ├── requirements.txt            ← flask, flask-cors, gunicorn, requests
│   └── Dockerfile                  ← Multi-stage lightweight Python container
├── frontend/
│   ├── app.py                      ← Flask reverse proxy + page server
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html              ← E-commerce Shop UI
│   │   └── lab.html                ← Interactive K8s & Microservices Lab Dashboard
│   └── static/
│       ├── style.css               ← Shop styling
│       ├── lab.css                 ← Lab & Protocol cards styling
│       ├── shop.js                 ← Shop interactivity & pod tracking
│       └── lab.js                  ← Experiments A–G logic & real-time telemetry
├── notification-service/
│   ├── app.py                      ← Async event receiver & live log consumer
│   ├── requirements.txt
│   └── Dockerfile                  ← Single-worker container for in-memory queue
├── k8s/
│   ├── backend-deployment.yaml     ← Backend Deployment + ClusterIP Service + Volume
│   ├── frontend-deployment.yaml    ← Frontend Deployment + NodePort Service
│   ├── notification-deployment.yaml← Notification Service Deployment + ClusterIP Service
│   └── loadbalancer-service.yaml   ← Optional Cloud/Tunnel LoadBalancer Service
├── start.ps1                       ← Fast 1-click start & port-forward script
├── stop.ps1                        ← Clean cluster shutdown script
├── deploy.ps1                      ← Full automated build & deploy script
├── GIT_COMMANDS.md                 ← Complete git reference & command history
└── README.md
```

---

## Architecture Overview

```
                      Browser / Client
                             │
                             │  HTTP :30080 (or port-forward :8080)
                             ▼
              NodePort Service (minimart-frontend-svc)
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   Frontend Pod 1     Frontend Pod 2     Frontend Pod 3
   (minimart-xxx)     (minimart-yyy)     (minimart-zzz)
          │                                     │
          │  HTTP /api/*                        │  HTTP /api/notify/*
          │  (Kubernetes DNS)                   │  (Kubernetes DNS)
          ▼                                     ▼
ClusterIP (minimart-backend-svc:5000)  ClusterIP (minimart-notification-svc:6000)
          │                                     ▲
     ┌────┴────────┐                            │  Async Event Push (fire-and-forget)
     ▼             ▼                            │  e.g. PRODUCT_CREATED, PRODUCT_UPDATED
Backend Pod 1  Backend Pod 2 ───────────────────┘
(SQLite DB)    (SQLite DB)
     │
     └──► /data/minimart.db (Persistent Storage)
```

---

## Prerequisites

- Windows 10/11
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2 or Hyper-V backend)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)
- PowerShell (pwsh)

Verify your environment:
```powershell
docker --version
minikube version
kubectl version --client
```

---

## Quick Start (Recommended)

### Option 1: Full Build & Deploy (First time or code changed)
```powershell
# Run the automated deployment script
.\deploy.ps1
```
This script will:
1. Ensure Minikube is started.
2. Configure Docker context to build directly inside Minikube's Docker daemon.
3. Build Docker images: `minimart-backend:latest`, `minimart-frontend:latest`, and `minimart-notification:latest`.
4. Apply all Kubernetes manifests in `/k8s`.
5. Wait for rollouts to finish and display the live URLs.

### Option 2: Quick Resume / Daily Use
If images and manifests are already deployed, start everything with:
```powershell
.\start.ps1
```
This will start Minikube, wait for all pods to be healthy, open the Lab in your browser, and set up port-forwarding on `http://localhost:8080`.

To stop the cluster cleanly when done:
```powershell
.\stop.ps1
```

---

## Accessing the Application

| View | Minikube IP URL | Localhost Port-Forward URL |
|---|---|---|
| **E-Commerce Shop** | `http://<minikube-ip>:30080` | `http://localhost:8080` |
| **Interactive K8s Lab** | `http://<minikube-ip>:30080/lab` | `http://localhost:8080/lab` |
| **Notification Events API** | `http://<minikube-ip>:30080/api/notify/events` | `http://localhost:8080/api/notify/events` |

---

## Interactive K8s Lab Experiments

Navigate to `/lab` in your browser to run interactive experiments:

### Experiment A: Request Routing & Load Balancing
Hit the backend multiple times and watch different Pod names handle the requests in real-time.

### Experiment B: Dynamic Pod Scaling
Scale the frontend or backend deployments from 1 to 5 replicas directly or via CLI:
```powershell
kubectl scale deployment minimart-frontend --replicas=5
kubectl get pods -l app=minimart-frontend -w
```

### Experiment C: Self-Healing Cluster
Kill a running pod and watch Kubernetes immediately spawn a replacement:
```powershell
kubectl delete pod <pod-name>
kubectl get pods -w
```

### Experiment D: Service Discovery & Endpoints Inspection
Inspect how Kubernetes manages IP mappings behind the ClusterIP:
```powershell
kubectl get endpoints minimart-backend-svc
kubectl get endpoints minimart-notification-svc
```

### Experiment E: Health Probes & Readiness Testing
Simulate health check failures and observe Kubernetes automatically pulling unhealthy pods from service traffic.

### Experiment F: Asynchronous Microservice Messaging
Create a test product and observe how the Backend processes the write, writes to SQLite, and fires an asynchronous fire-and-forget event to the Notification Service without blocking the client.

### Experiment G: Microservice Protocol Benchmarking
Interactive comparison of:
- **REST / HTTP 1.1**: Simple, text/JSON based, ubiquitous but higher overhead.
- **gRPC / HTTP/2**: Protocol Buffers, multiplexed, binary, highly performant for internal microservices.
- **WebSockets**: Full-duplex persistent connections for live feeds and chat.
- **Event-Driven / Broker (Kafka/RabbitMQ)**: Message queuing, loose coupling, guaranteed delivery.

---

## Helpful Commands Cheatsheet

```powershell
# View all pods, services, and deployments
kubectl get all

# View live pod logs
kubectl logs -l app=minimart-backend -f --prefix
kubectl logs -l app=minimart-frontend -f --prefix
kubectl logs -l app=minimart-notification -f --prefix

# Perform a rolling update
kubectl set env deployment/minimart-backend APP_VERSION=2.0.0
kubectl rollout status deployment/minimart-backend
kubectl rollout undo deployment/minimart-backend
```

For a comprehensive log and explanation of all Git commands used throughout this repository, refer to [GIT_COMMANDS.md](file:///e:/kubernetes_project/GIT_COMMANDS.md).
