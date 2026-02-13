# Deployment Guide for FishCurrent on Render

## Issue Diagnosed: Server Error 500

### Root Cause
The 500 error occurs due to missing database migrations. The error message is:
```
django.db.utils.OperationalError: no such column: store_product.original_price
```

This happens when the database schema is out of sync with the application code.

## Solution

### Step 1: Configure Database (CRITICAL)
The most common cause of this issue is **using SQLite in production**, which is ephemeral on Render. You MUST use a persistent database.

1. **In Render Dashboard**, go to your service's Environment variables
2. **Add or verify** the `DATABASE_URL` environment variable points to your Neon PostgreSQL database
   - Format: `postgresql://username:password@host/database`
   - If using Neon: Get the connection string from your Neon dashboard
3. **Important**: Without DATABASE_URL, the app defaults to SQLite which gets wiped on each deploy

### Step 2: Redeploy
Once DATABASE_URL is configured:
1. Go to your Render dashboard
2. Click "Manual Deploy" → "Deploy latest commit"
3. The `build.sh` script will automatically run migrations during deployment

### Step 3: Verify
After deployment completes:
1. Visit your site at https://fishocean.onrender.com
2. You should see the landing page without errors
3. Check Render logs if issues persist

## Troubleshooting

### If migrations still fail:
1. Check Render build logs for migration errors
2. Ensure all migration files are committed to the repository
3. Verify database connectivity from Render

### If DATABASE_URL is set but still using SQLite:
- The URL might have extra whitespace or quotes
- Try removing and re-adding the environment variable
- Ensure there are no typos in the variable name (it's case-sensitive: `DATABASE_URL`)

### Manual Migration (if needed):
If you need to run migrations manually:
1. Use Render Shell (Dashboard → Shell)
2. Run: `python manage.py migrate`

## What build.sh does:
```bash
#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations (THIS FIXES THE ERROR)
python manage.py migrate
```

The migration step runs automatically during each deployment.

## Summary
✅ The code is correct
✅ The build script is correct  
❌ **The DATABASE_URL environment variable must be configured in Render**

Once DATABASE_URL is set to a persistent database (PostgreSQL/Neon), the migrations will run successfully and the 500 error will be resolved.
