Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🤖 Deploying Franka Panda Robot to Docker Desktop..." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

Write-Host "`n[1/3] Building Docker image and starting container..." -ForegroundColor Yellow
docker compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "✅ Container successfully deployed to Docker Desktop!" -ForegroundColor Green
    Write-Host "`n📌 Docker Desktop Application:" -ForegroundColor Yellow
    Write-Host "   Container Name: 'panda_robot_stack' (Status: Running)"
    Write-Host "   Port: 5000:5000"
    Write-Host "`n🌐 Open Web Dashboard in your browser:" -ForegroundColor Cyan
    Write-Host "   👉 http://localhost:5000" -ForegroundColor Cyan
    Write-Host "========================================================`n" -ForegroundColor Green

    Start-Process "http://localhost:5000"
} else {
    Write-Host "`n[ERROR] Docker command failed. Please verify that Docker Desktop is running." -ForegroundColor Red
}
