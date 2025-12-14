#!/usr/bin/env bash
# Validate setup before Render deployment

echo "🔍 Validating Finance Tracker V2 setup..."
echo ""

ERRORS=0

# Check Python version
echo "✓ Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; ERRORS=$((ERRORS+1)); }

# Check required files
echo "✓ Checking required files..."
FILES=("requirements.txt" "render.yaml" "alembic.ini" "app/main.py" "scripts/render-build.sh")
for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing file: $file"
        ERRORS=$((ERRORS+1))
    fi
done

# Check alembic migrations
echo "✓ Checking database migrations..."
if [ ! -d "alembic/versions" ]; then
    echo "❌ Missing alembic/versions directory"
    ERRORS=$((ERRORS+1))
fi

MIGRATION_COUNT=$(ls -1 alembic/versions/*.py 2>/dev/null | wc -l)
if [ "$MIGRATION_COUNT" -eq 0 ]; then
    echo "❌ No migration files found"
    ERRORS=$((ERRORS+1))
fi

# Check Python imports
echo "✓ Checking Python imports..."
python3 -c "import fastapi; import uvicorn; import sqlalchemy; import alembic" 2>/dev/null || {
    echo "⚠️  Some dependencies not installed (run: pip install -r requirements.txt)"
}

# Check render.yaml syntax
echo "✓ Checking render.yaml..."
if ! grep -q "buildCommand.*render-build.sh" render.yaml; then
    echo "⚠️  render.yaml might not be configured correctly"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Ready for Render deployment."
    echo ""
    echo "Next steps:"
    echo "1. git add ."
    echo "2. git commit -m 'Ready for Render deployment'"
    echo "3. git push origin main"
    echo "4. Deploy on Render Dashboard"
    exit 0
else
    echo "❌ Found $ERRORS error(s). Please fix before deploying."
    exit 1
fi
