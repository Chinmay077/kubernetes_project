#!/usr/bin/env pwsh
# ============================================================
# MiniMart Kubernetes Learning Lab – Windows Deploy Script
# Requires: Docker Desktop (with Minikube driver), kubectl
# ============================================================
param(
    [switch]$Clean,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    ✓ $msg"  -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    ⚠ $msg"  -ForegroundColor Yellow }

# ── Stop / Clean ─────────────────────────────────────────────────────────
if ($Stop) {
    Write-Step "Stopping Minikube cluster"
    minikube stop
    exit 0
}

if ($Clean) {
    Write-Step "Deleting Minikube cluster (full reset)"
    minikube delete
    Write-Ok "Cluster deleted. Re-run without -Clean to rebuild."
    exit 0
}

# ── 1. Start Minikube ─────────────────────────────────────────────────────
Write-Step "Starting Minikube"
$status = minikube status --format='{{.Host}}' 2>$null
if ($status -eq "Running") {
    Write-Ok "Minikube already running"
} else {
    minikube start --driver=docker --cpus=2 --memory=3g
    Write-Ok "Minikube started"
}

# ── 2. Point Docker CLI at Minikube's Docker daemon ───────────────────────
Write-Step "Configuring Docker to use Minikube's daemon"
Write-Warn "Running: minikube docker-env --shell powershell | Invoke-Expression"
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
Write-Ok "Docker context switched to Minikube"

# ── 3. Build images inside Minikube ──────────────────────────────────────
Write-Step "Building Backend image (minimart-backend:latest)"
docker build -t minimart-backend:latest ./backend
Write-Ok "Backend image built"

Write-Step "Building Frontend image (minimart-frontend:latest)"
docker build -t minimart-frontend:latest ./frontend
Write-Ok "Frontend image built"

# ── 4. Apply Kubernetes manifests ────────────────────────────────────────
Write-Step "Applying Kubernetes manifests"
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
Write-Ok "Manifests applied"

# ── 5. Wait for rollout ───────────────────────────────────────────────────
Write-Step "Waiting for backend rollout"
kubectl rollout status deployment/minimart-backend --timeout=90s

Write-Step "Waiting for frontend rollout"
kubectl rollout status deployment/minimart-frontend --timeout=90s

# ── 6. Show status ────────────────────────────────────────────────────────
Write-Step "Cluster Status"
kubectl get pods,svc -o wide

# ── 7. Print access URL ───────────────────────────────────────────────────
Write-Step "Getting access URL"
$ip = minikube ip
$url = "http://${ip}:30080"
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "  ║  MiniMart is running!                            ║" -ForegroundColor Magenta
Write-Host "  ║                                                  ║" -ForegroundColor Magenta
Write-Host "  ║  Shop:      $url             ║" -ForegroundColor Magenta
Write-Host "  ║  K8s Lab:   $url/lab         ║" -ForegroundColor Magenta
Write-Host "  ║                                                  ║" -ForegroundColor Magenta
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Alternatively run:" -ForegroundColor Gray
Write-Host "    minikube service minimart-frontend-svc --url" -ForegroundColor Gray
Write-Host ""
Write-Host "  To tail all logs:" -ForegroundColor Gray
Write-Host "    kubectl logs -l app=minimart-frontend -f --prefix" -ForegroundColor Gray
Write-Host "    kubectl logs -l app=minimart-backend  -f --prefix" -ForegroundColor Gray
