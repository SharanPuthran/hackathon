# Mock Solution Switching Guide

This guide explains how to switch between different mock solution files in the SkyMarshal frontend.

## Available Solutions

The frontend includes 6 pre-loaded mock solutions:

- `solution_1` - Default solution
- `solution_2` - Alternative scenario
- `solution_3` - Alternative scenario
- `solution_4` - Alternative scenario
- `solution_5` - Alternative scenario
- `solution_6` - Alternative scenario

## Method 1: Environment Variable (Requires Restart)

Edit `frontend/.env` and set:

```env
VITE_MOCK_SOLUTION=solution_3
```

Then **restart the dev server**:

```bash
cd frontend
npm run dev
```

**Note**: Vite doesn't hot-reload environment variables, so you must restart the dev server for changes to take effect.

## Method 2: Runtime Switching (No Restart Required)

Open your browser's developer console and use these commands:

### Switch to a different solution

```javascript
window.switchMockSolution("solution_3");
```

### List available solutions

```javascript
window.getAvailableSolutions();
```

### Clear override and use .env value

```javascript
window.clearMockSolution();
```

After switching, submit a new query or refresh the page to see the new solution.

## Method 3: URL Parameter (Coming Soon)

Future enhancement: Add URL parameter support like `?mockSolution=solution_3`

## Troubleshooting

### Solution not loading after changing .env

- **Cause**: Vite caches environment variables at startup
- **Fix**: Restart the dev server with `npm run dev`

### Console commands not working

- **Cause**: App hasn't loaded the switcher utility yet
- **Fix**: Refresh the page and try again

### Still seeing old solution after switching

- **Cause**: Browser may have cached the response
- **Fix**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R) or clear browser cache

## Current Configuration

To check which solution is currently configured:

```javascript
// In browser console
console.log(import.meta.env.VITE_MOCK_SOLUTION);
```

## Mock Mode Settings

Mock mode must be enabled for solutions to load:

```env
# In frontend/.env
VITE_ENABLE_MOCK=true
```

When mock mode is disabled, the app will make real API calls instead of using mock data.
