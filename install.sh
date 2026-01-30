#!/bin/bash

# SkyMarshal Installation Script

echo "=========================================="
echo "SkyMarshal Installation"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys and database credentials"
fi

# Check PostgreSQL
echo ""
echo "Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL found"
    
    # Check if database exists
    if psql -lqt | cut -d \| -f 1 | grep -qw etihad_aviation; then
        echo "✅ Database 'etihad_aviation' exists"
    else
        echo "⚠️  Database 'etihad_aviation' not found"
        echo "   Run: createdb etihad_aviation"
        echo "   Then: psql -d etihad_aviation -f database_schema.sql"
    fi
else
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL 13+"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Setup database:"
echo "     createdb etihad_aviation"
echo "     psql -d etihad_aviation -f database_schema.sql"
echo "     python generate_data.py"
echo "  3. Test system: python test_system.py"
echo "  4. Run demo: python run_demo.py"
echo "  5. Run dashboard: streamlit run app.py"
echo ""
