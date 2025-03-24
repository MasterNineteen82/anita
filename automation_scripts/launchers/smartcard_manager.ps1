# Converted from SmartyCardManager.bat
# Smartcard Manager PowerShell Script

$ProjectRoot = "K:\anita\poc"

Write-Host "Starting Smartcard Manager..." -ForegroundColor Green
python "$ProjectRoot\backend\services\smartcard_service.py"
