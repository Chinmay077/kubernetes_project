Write-Host "==> Starting Minikube cluster..." -ForegroundColor Cyan
minikube start

Write-Host "`n==> Waiting for Pods to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=minimart-backend      --timeout=90s
kubectl wait --for=condition=ready pod -l app=minimart-frontend     --timeout=90s
kubectl wait --for=condition=ready pod -l app=minimart-notification --timeout=60s

Write-Host "`n==> Cluster Pods Status:" -ForegroundColor Green
kubectl get pods -o wide

Write-Host "`n==> Opening MiniMart in Browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8080/lab"

Write-Host "`n============================================================" -ForegroundColor Magenta
Write-Host "  MiniMart is LIVE!" -ForegroundColor Magenta
Write-Host "  Shop:          http://localhost:8080" -ForegroundColor Magenta
Write-Host "  K8s Lab:       http://localhost:8080/lab" -ForegroundColor Magenta
Write-Host "  Notif Events:  http://localhost:8080/api/notify/events" -ForegroundColor Magenta
Write-Host "============================================================`n" -ForegroundColor Magenta
Write-Host "Press Ctrl+C anytime to stop port forwarding.`n" -ForegroundColor Yellow

# Port forward keeps the connection active to localhost:8080
kubectl port-forward svc/minimart-frontend-svc 8080:8080
