@echo off
REM Quick start script for AI Document Search (Windows)

echo.
echo 🚀 AI Document Search - Quick Start
echo ====================================
echo.

REM Check if .env exists
if not exist .env (
    echo ⚠️  No .env file found. Creating from template...
    copy env.example .env
    echo ✅ Created .env file
    echo.
    echo ⚠️  IMPORTANT: Edit .env and set your OPENAI_API_KEY
    echo    notepad .env
    echo.
    pause
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

echo 📦 Building and starting services...
echo.

REM Start services
docker-compose up --build -d

echo.
echo ✅ Services started!
echo.
echo 🌐 Access the application:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 📊 View logs:
echo    docker-compose logs -f
echo.
echo 🛑 Stop services:
echo    docker-compose down
echo.
echo 🔧 For development without Docker, see DEPLOYMENT.md
echo.
pause

