#!/usr/bin/env pwsh
# ============================================================
# MiniMart Quick Stop Script
# Cluster band karne ke liye: .\stop.ps1
# ============================================================

Write-Host "==> Stopping Minikube cluster safely..." -ForegroundColor Yellow
minikube stop
Write-Host "✓ Minikube stopped safely. RAM aur CPU free ho gaye!" -ForegroundColor Green
