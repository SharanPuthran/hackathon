# Quick Fix: Solution Not Loading

## The Problem

You changed `VITE_MOCK_SOLUTION` in `.env` but the UI kept loading the old solution.

## Root Cause

**`.env.local` was overriding `.env`!** Vite gives `.env.local` higher priority than `.env`.

## The Fix (3 Steps)

### Step 1: Check Which File to Edit

```bash
cd frontend
./check-env-config.sh
```

This shows which file Vite is actually using.

### Step 2: Edit the Correct File

**If you have `.env.local`** (most common):

```bash
# Edit frontend/.env.local
VITE_ENABLE_MOCK=true
VITE_MOCK_SOLUTION=solution_6
```

**If you only have `.env`**:

```bash
# Edit frontend/.env
VITE_ENABLE_MOCK=true
VITE_MOCK_SOLUTION=solution_6
```

### Step 3: Restart Dev Server

```bash
# Stop server (Ctrl+C)
npm run dev
```

**That's it!** The new solution will now load.

## Why This Happens

Vite (the build tool) reads environment variables when the dev server starts. It doesn't automatically reload them when you change the `.env` file. You must restart the server.

## Alternative: Switch Without Restarting

If you don't want to restart the server every time:

1. Open browser console (F12)
2. Run: `window.switchMockSolution('solution_6')`
3. Submit a new query

This switches solutions instantly without restarting!

## Verify It's Working

After restarting, check the browser console. You should see:

```
[MockResponse] Loading solution: solution_6
```

## Still Not Working?

1. **Hard refresh the browser**: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
2. **Clear browser cache**: Open DevTools → Application → Clear Storage → Clear site data
3. **Check console for errors**: Look for any red error messages
4. **Verify solution file exists**: Check that `frontend/data/responses/solution_6.json` exists

## Need Help?

See `MOCK_SOLUTION_GUIDE.md` for detailed documentation.
