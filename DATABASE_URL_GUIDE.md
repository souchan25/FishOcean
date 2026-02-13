# DATABASE_URL Configuration Guide

## Your Connection String

You provided:
```
psql 'postgresql://neondb_owner:npg_EcP7OlMhL5NK@ep-winter-recipe-ai32e2lm-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&amp;channel_binding=require'
```

## ⚠️ Issues Identified

### 1. HTML Entity (`&amp;`)
The string contains `&amp;` which is HTML-encoded. It should be a plain `&` (ampersand).

### 2. Includes `psql` command
The string starts with `psql '...'` which is the command-line tool prefix.

## ✅ Correct Format

For the `DATABASE_URL` environment variable in Render, use:

```
postgresql://neondb_owner:npg_EcP7OlMhL5NK@ep-winter-recipe-ai32e2lm-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

**Key changes:**
- ❌ `psql '...'` → ✅ Removed command prefix and quotes
- ❌ `&amp;` → ✅ `&` (plain ampersand)

## Good News! 🎉

**The application now automatically handles both issues!**

The updated `settings.py` includes:
- ✅ Automatically strips `psql` command prefix
- ✅ Automatically removes surrounding quotes
- ✅ Automatically converts `&amp;` to `&`
- ✅ Converts `postgresql://` to `postgres://` (as required by some Django versions)

## How to Set in Render

1. Go to your Render Dashboard
2. Select your `fishcurrent` service
3. Go to **Environment** tab
4. Add or edit `DATABASE_URL` variable
5. Paste either format:
   - **Best**: `postgresql://neondb_owner:npg_EcP7OlMhL5NK@ep-winter-recipe-ai32e2lm-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   - **Also works**: Your original string with `psql` and `&amp;` (the app will clean it)
6. Click **Save Changes**
7. Trigger a new deploy

## Verification

After deployment, check the logs for these messages:
```
Render Debug: Processing DATABASE_URL. Length: ...
Render Debug: Start of URL: postgres://...
Render Debug: Successfully configured database.
```

If you see these messages, your database is configured correctly!

## Why Both Issues Occurred

1. **`psql` prefix**: Neon provides this for direct command-line connection. You just need the URL part for Django.
2. **`&amp;` encoding**: Web interfaces often HTML-encode URLs. Copy from the "Connection String" field, not from rendered HTML.

## Still Having Issues?

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive troubleshooting.
