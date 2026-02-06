# Mock Solution Switching Fix

## Problem

The frontend was stuck loading `solution_2` even when `VITE_MOCK_SOLUTION` was changed to `solution_6` in the `.env` file. The issue occurred because:

1. **Static imports**: Solution JSON files were imported statically at module load time
2. **Cached config**: The environment config was cached when the module first loaded
3. **No hot reload**: Vite doesn't hot-reload environment variables without a server restart

## Solution

### 1. Dynamic Solution Loading

Changed from static imports to dynamic imports:

**Before:**

```typescript
import solution1 from "./responses/solution_1.json";
import solution2 from "./responses/solution_2.json";
// ... etc

const SOLUTIONS_REGISTRY = {
  solution_1: solution1,
  solution_2: solution2,
  // ... etc
};
```

**After:**

```typescript
async function loadSolutions(): Promise<Record<string, MockResponse>> {
  const [solution1, solution2, ...] = await Promise.all([
    import('./responses/solution_1.json'),
    import('./responses/solution_2.json'),
    // ... etc
  ]);

  return {
    'solution_1': solution1.default,
    'solution_2': solution2.default,
    // ... etc
  };
}
```

### 2. Async Mock Response Generation

Changed `getMockStatusResponse()` from synchronous to asynchronous:

**Before:**

```typescript
export function getMockStatusResponse(): any {
  const selectedSolution = getSelectedSolution();
  return { ... };
}
```

**After:**

```typescript
export async function getMockStatusResponse(): Promise<any> {
  const selectedSolution = await getSelectedSolution();
  return { ... };
}
```

### 3. Runtime Solution Switching

Added a new utility (`mockSolutionSwitcher.ts`) that allows switching solutions without restarting:

```typescript
// In browser console
window.switchMockSolution("solution_3");
window.getAvailableSolutions();
window.clearMockSolution();
```

## How to Use

### Method 1: Environment Variable (Recommended for Development)

1. Edit `frontend/.env`:

   ```env
   VITE_MOCK_SOLUTION=solution_6
   ```

2. **Restart the dev server**:
   ```bash
   cd frontend
   npm run dev
   ```

### Method 2: Runtime Switching (No Restart)

1. Open browser console
2. Run: `window.switchMockSolution('solution_6')`
3. Submit a new query or refresh the page

### Method 3: Test Page

Open `frontend/test-solution-switching.html` in your browser for a visual interface to switch solutions.

## Files Changed

1. `frontend/data/mockResponse.ts` - Made solution loading dynamic and async
2. `frontend/services/apiAsync.ts` - Updated to await async mock response
3. `frontend/utils/mockSolutionSwitcher.ts` - New utility for runtime switching
4. `frontend/App.tsx` - Import switcher utility to expose console commands

## Files Created

1. `frontend/MOCK_SOLUTION_GUIDE.md` - User guide for switching solutions
2. `frontend/test-solution-switching.html` - Visual test interface
3. `frontend/SOLUTION_SWITCHING_FIX.md` - This document

## Testing

1. Verify current solution in `.env`: `VITE_MOCK_SOLUTION=solution_6`
2. Restart dev server: `cd frontend && npm run dev`
3. Open app in browser
4. Submit a query - should load solution_6
5. Open console and run: `window.switchMockSolution('solution_3')`
6. Submit another query - should load solution_3

## Notes

- Solutions are cached after first load for performance
- Changing `.env` requires dev server restart
- Runtime switching via console doesn't require restart
- All 6 solutions are bundled in the build
