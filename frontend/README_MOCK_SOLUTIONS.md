# 🎭 Mock Solutions - Quick Reference

## TL;DR

**Problem**: UI stuck on old solution after changing `.env`  
**Fix**: Restart dev server OR use `window.switchMockSolution('solution_X')` in console

---

## 🚀 Quick Start

### Method 1: Environment Variable (Recommended)

```bash
# 1. Edit frontend/.env
VITE_MOCK_SOLUTION=solution_6

# 2. Restart dev server
npm run dev
```

### Method 2: Runtime Switching (Instant)

```javascript
// In browser console (F12)
window.switchMockSolution("solution_6");
```

---

## 📋 Available Solutions

| Solution   | File              | Size | Description          |
| ---------- | ----------------- | ---- | -------------------- |
| solution_1 | `solution_1.json` | 164K | Default scenario     |
| solution_2 | `solution_2.json` | 160K | Alternative scenario |
| solution_3 | `solution_3.json` | 108K | Alternative scenario |
| solution_4 | `solution_4.json` | 120K | Alternative scenario |
| solution_5 | `solution_5.json` | 108K | Alternative scenario |
| solution_6 | `solution_6.json` | 144K | Alternative scenario |

---

## 🎮 Console Commands

Open browser console (F12) and use:

```javascript
// Switch solution
window.switchMockSolution("solution_3");

// List available
window.getAvailableSolutions();

// Clear override
window.clearMockSolution();
```

---

## 🧪 Test & Verify

```bash
# Run verification script
cd frontend
./test-mock-loading.sh
```

Expected: ✅ All checks passed!

---

## 🔧 Configuration

### Enable Mock Mode

```env
# frontend/.env
VITE_ENABLE_MOCK=true
VITE_MOCK_SOLUTION=solution_6
```

### Disable Mock Mode (Use Real API)

```env
# frontend/.env
VITE_ENABLE_MOCK=false
```

---

## 📖 Documentation

- **Quick Fix**: `QUICK_FIX_GUIDE.md` - Solve common issues
- **Full Guide**: `MOCK_SOLUTION_GUIDE.md` - Complete documentation
- **Technical**: `SOLUTION_SWITCHING_FIX.md` - Implementation details
- **Status**: `SOLUTION_LOADING_COMPLETE.md` - Fix summary

---

## 🐛 Troubleshooting

### Solution not loading?

1. ✅ Check `.env`: `VITE_ENABLE_MOCK=true`
2. ✅ Restart dev server: `npm run dev`
3. ✅ Hard refresh browser: `Ctrl+Shift+R`
4. ✅ Check console for errors

### Still stuck?

```bash
# Verify everything
./test-mock-loading.sh

# Check console logs
# Look for: [MockResponse] Loading solution: solution_X
```

---

## 💡 Tips

- **Restart required**: Changing `.env` requires dev server restart
- **No restart needed**: Console commands work instantly
- **Check logs**: Console shows which solution is loading
- **Test page**: Open `test-solution-switching.html` for GUI

---

## ✅ Current Status

- Mock Mode: **Enabled**
- Current Solution: **solution_6**
- All Solutions: **Available** (6 files)
- Runtime Switching: **Working**

---

**Need help?** See `QUICK_FIX_GUIDE.md` or `MOCK_SOLUTION_GUIDE.md`
