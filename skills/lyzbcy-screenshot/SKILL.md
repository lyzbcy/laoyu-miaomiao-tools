---
name: lyzbcy-screenshot
description: Capture screen or window screenshots. Use when user asks to "screenshot", "截屏", "截图", "take a screenshot", "capture screen", or needs visual context from the current desktop. Handles DPI scaling issues on Windows automatically. Custom skill with auto-cleanup (15 days retention).
---

中文名称：屏幕截图
能力简介：捕获屏幕或窗口截图，自动处理 Windows DPI 缩放问题。

# Screenshot / 屏幕截图

A skill for capturing screenshots with proper DPI handling.

## When to Use

- User requests a screenshot / 截图 / 截屏
- Need visual context from the desktop
- Monitoring screen state remotely

## 📁 Storage & Cleanup

### Screenshot Directory

All screenshots are stored in:
```
<workspace>/screenshots/
```

Where `<workspace>` is the OpenClaw workspace directory (typically `~/.openclaw/workspace`).

### 🧹 Auto-Cleanup Rule

**Screenshots older than 15 days are automatically deleted.**

**When to check:** Every time this skill is invoked, run cleanup check BEFORE capturing the screenshot.

**Cleanup command:**
```powershell
$screenshotDir = "<workspace>/screenshots"
$cutoffDate = (Get-Date).AddDays(-15)
if (Test-Path $screenshotDir) {
    Get-ChildItem $screenshotDir -Filter "*.png" | 
        Where-Object { $_.LastWriteTime -lt $cutoffDate } | 
        Remove-Item -Force
}
```

### Workflow

1. **Check cleanup** — Delete expired screenshots
2. **Capture** — Take new screenshot
3. **Return** — Provide path to user

This keeps storage lean without manual intervention.

## Windows Screenshot

### ⚠️ DPI Scaling Issue

On Windows with display scaling (125%, 150%, etc.), naive screenshot methods capture at the **scaled logical size**, not the actual resolution. For example, a 2560x1440 display at 150% scaling would incorrectly capture at ~1707x960.

**Solution:** Enable DPI awareness before capturing.

### Recommended Method

Use the bundled script at `scripts/screenshot.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File "<skill-path>/scripts/screenshot.ps1" -OutputPath "<output-path>"
```

Or inline:

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Enable DPI awareness (critical for correct resolution)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DPISupport {
    [DllImport(\"user32.dll\")]
    public static extern bool SetProcessDPIAware();
}
"@
[DPISupport]::SetProcessDPIAware() | Out-Null

# Capture screenshot
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$b = $screen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($b.X, $b.Y, 0, 0, $b.Size)

# Save
$bitmap.Save("<output-path>", [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
$graphics.Dispose()
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `-OutputPath` | Where to save the screenshot (default: temp directory) |

## Multi-Monitor Support

For systems with multiple monitors, use `VirtualScreen` to capture all:

```powershell
$virtualScreen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $virtualScreen.Width, $virtualScreen.Height
$graphics.CopyFromScreen($virtualScreen.Location, [System.Drawing.Point]::Empty, $virtualScreen.Size)
```

## Extension Points

- **Other platforms:** See `references/macos.md` and `references/linux.md` (to be added)
- **Window-specific:** Can be extended with `FindWindow` + `PrintWindow` for specific window capture
- **Region capture:** Can be extended with coordinate parameters

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Screenshot is smaller than actual resolution | DPI scaling | Call `SetProcessDPIAware()` first |
| Only captures one monitor | Using `PrimaryScreen` | Use `VirtualScreen` for all monitors |
| Black/blank screenshot | Session locked or UAC prompt | Cannot capture secure desktop |

## Output

Returns the path to the saved PNG file.
