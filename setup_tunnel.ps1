Write-Host "Setting up secure tunnel for backend..." -ForegroundColor Cyan

if (Get-Command ngrok -ErrorAction SilentlyContinue) {
    Write-Host "✅ ngrok is already installed!" -ForegroundColor Green
    Write-Host "Starting tunnel on port 8000..." -ForegroundColor Cyan
    ngrok http 8000
} else {
    Write-Host "⚠️ ngrok not found." -ForegroundColor Yellow
    Write-Host "Attempting to install via winget..." -ForegroundColor Cyan
    winget install --id Ngrok.Ngrok -e --accept-source-agreements --accept-package-agreements
    
    if ($?) {
        Write-Host "✅ Installation complete! Please restart this terminal." -ForegroundColor Green
        Write-Host "After restarting, run this script again." -ForegroundColor Cyan
    } else {
        Write-Host "❌ Automated installation failed." -ForegroundColor Red
        Write-Host "Please download ngrok manually from: https://ngrok.com/download"
        Write-Host "Once installed, run this script again."
    }
}
