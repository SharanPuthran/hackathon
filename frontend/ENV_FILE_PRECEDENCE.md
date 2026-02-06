# 🔧 Vite Environment File Precedence

## The Real Problem

You were editing `.env` but the app was loading from `.env.local` which has **higher priority**!

## Vite Environment File Priority

Vite loads environment files in this order (highest to lowest):

```
1. .env.local          ← HIGHEST PRIORITY (overrides everything)
2. .env.development    ← Only in dev mode
3. .env.production     ← Only in production
4. .env                ← Base configuration
5. .env.example        ← Template only (not loaded)
```

**Important**: `.env.local` always wins! If a variable exists in both `.env` and `.env.local`, the value from `.env.local` is used.

## Your Situation

You had:

**`.env`** (you were editing this):

```env
VITE_MOCK_SOLUTION=solution_6
VITE_ENABLE_MOCK=true
```

**`.env.local`** (this was actually being used):

```env
VITE_MOCK_SOLUTION=solution_2  ← This was winning!
VITE_ENABLE_MOCK=false
```

Result: App loaded `solution_2` from `.env.local`, ignoring your `.env` changes.

## Solution

I've updated **`.env.local`** to:

```env
VITE_MOCK_SOLUTION=solution_6
VITE_ENABLE_MOCK=true
```

## What to Do Now

**Restart your dev server:**

```bash
# Stop the server (Ctrl+C)
npm run dev
```

The app will now load `solution_6`!

## Best Practices

### Option 1: Use .env.local for Local Development (Recommended)

- Keep `.env` as the base/default configuration
- Use `.env.local` for your personal local settings
- `.env.local` is gitignored by default (won't be committed)

**When to edit:**

- Edit `.env.local` for your local development
- Edit `.env` for team-wide defaults

### Option 2: Delete .env.local

If you don't need separate local config:

```bash
rm .env.local
```

Then the app will use `.env` directly.

## Quick Reference

### Check which file is being used:

```bash
# List all env files
ls -la frontend/.env*

# Check values
cat frontend/.env
cat frontend/.env.local
```

### Priority reminder:

```
.env.local > .env > .env.example
```

### After changing any .env file:

```bash
# ALWAYS restart the dev server
npm run dev
```

## Debugging Tips

### Check what Vite is loading:

Add this to your code temporarily:

```typescript
console.log("VITE_MOCK_SOLUTION:", import.meta.env.VITE_MOCK_SOLUTION);
console.log("VITE_ENABLE_MOCK:", import.meta.env.VITE_ENABLE_MOCK);
```

### Verify in browser console:

```javascript
// Check current config
console.log(import.meta.env.VITE_MOCK_SOLUTION);
```

## Common Mistakes

❌ **Editing .env but .env.local exists**

- Solution: Edit .env.local instead

❌ **Not restarting dev server**

- Solution: Always restart after env changes

❌ **Editing .env.example**

- Solution: This is just a template, edit .env or .env.local

## Summary

✅ **Fixed**: Updated `.env.local` to use `solution_6`  
✅ **Action**: Restart dev server  
✅ **Remember**: `.env.local` overrides `.env`

---

**Current Configuration:**

- File: `.env.local` (highest priority)
- Mock Mode: `true`
- Solution: `solution_6`
