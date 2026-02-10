Write-Host "Setting up backend tunnel using localtunnel..." -ForegroundColor Cyan

# Force add Node.js to the current session's PATH so npx can find 'node'
$env:Path = "C:\Program Files\nodejs;" + $env:Path

if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "✅ Node.js found!" -ForegroundColor Green
    Write-Host "Starting tunnel on port 8000..." -ForegroundColor Cyan
    Write-Host "You will see a URL like: https://something.loca.lt" -ForegroundColor Yellow
    Write-Host "⚠️ IMPORTANT: When you visit the URL, the password is your IP address." -ForegroundColor Red
    
    # Use npx directly since it should now be in the path
    npx localtunnel --port 8000
} else {
    Write-Host "❌ Node.js still not found." -ForegroundColor Red
    Write-Host "Please restart your terminal to fix the PATH issue."
}
