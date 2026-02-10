Write-Host "Setting up backend tunnel using SSH (Serveo)..." -ForegroundColor Cyan
Write-Host "This method uses SSH and might bypass some firewalls." -ForegroundColor Yellow
Write-Host "If this also hangs, we must use the Manual Data Sync method." -ForegroundColor Red

# Check if SSH is available
if (Get-Command ssh -ErrorAction SilentlyContinue) {
    Write-Host "✅ SSH client found!" -ForegroundColor Green
    Write-Host "Connecting to serveo.net..." -ForegroundColor Cyan
    Write-Host "If asked, type 'yes' to continue connecting." -ForegroundColor Yellow
    
    # Connect to serveo.net
    # -R 80:localhost:8000 -> Forward remote port 80 to local 8000
    ssh -R 80:localhost:8000 serveo.net
} else {
    Write-Host "❌ SSH client not found." -ForegroundColor Red
}
