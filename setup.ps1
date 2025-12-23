# Luxury Travel Bot - Windows Setup Script
# Run this with: .\setup.ps1

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Luxury Travel Bot - Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python 3 is installed
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Host "Error: Python is not installed" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from python.org and try again"
    exit 1
}

Write-Host "✓ Python found" -ForegroundColor Green
python --version
Write-Host ""

# Check if pip is installed
$pipCommand = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pipCommand) {
    Write-Host "Error: pip is not installed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ pip found" -ForegroundColor Green
Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..."
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Install requirements
Write-Host "Installing dependencies..."
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "Error installing dependencies" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..."
    Copy-Item .env.example .env
    Write-Host "⚠ Please edit .env and add your OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# Create storage directory
Write-Host "Creating storage directory..."
New-Item -ItemType Directory -Force -Path "tmp\travel-pdfs" | Out-Null
Write-Host "✓ Storage directory created" -ForegroundColor Green
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setup Complete! ✨" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file and add your OPENAI_API_KEY"
Write-Host "2. Run the bot:"
Write-Host "   venv\Scripts\Activate.ps1"
Write-Host "   python Luxury_Travel_Bot.py"
Write-Host ""
Write-Host "3. Test the bot:"
Write-Host "   python test_bot.py"
Write-Host ""
Write-Host "4. Open in browser:"
Write-Host "   http://localhost:8080"
Write-Host ""