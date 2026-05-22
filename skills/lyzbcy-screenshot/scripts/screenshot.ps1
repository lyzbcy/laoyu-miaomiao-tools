<#
.SYNOPSIS
    Capture a screenshot with proper DPI handling and auto-cleanup.

.DESCRIPTION
    Captures the primary screen or all screens (virtual desktop).
    Automatically handles Windows DPI scaling issues.
    Cleans up screenshots older than 15 days before capturing.

.PARAMETER OutputPath
    Path to save the screenshot. Default: <workspace>/screenshots/screenshot_<timestamp>.png

.PARAMETER AllScreens
    Capture all monitors (virtual desktop). Default: capture primary screen only.

.PARAMETER SkipCleanup
    Skip the auto-cleanup of old screenshots. Default: cleanup enabled.

.PARAMETER WorkspacePath
    Path to OpenClaw workspace. Default: C:\Users\<user>\.openclaw\workspace

.EXAMPLE
    .\screenshot.ps1
    Captures primary screen, cleans up old files, saves to workspace/screenshots/

.EXAMPLE
    .\screenshot.ps1 -OutputPath "C:\Users\user\Desktop\capture.png"
    Captures primary screen to specified path.

.EXAMPLE
    .\screenshot.ps1 -AllScreens
    Captures all monitors.

.NOTES
    Requires Windows with .NET Framework.
    Must call SetProcessDPIAware() before System.Windows.Forms loads to handle scaling correctly.
#>

param(
    [string]$OutputPath = "",
    [switch]$AllScreens,
    [switch]$SkipCleanup,
    [string]$WorkspacePath = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Enable DPI awareness - MUST be done before getting screen bounds
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DPISupport {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
"@
[DPISupport]::SetProcessDPIAware() | Out-Null

# Determine workspace path
if ([string]::IsNullOrEmpty($WorkspacePath)) {
    $WorkspacePath = Join-Path $env:USERPROFILE ".openclaw\workspace"
}

# Screenshot directory
$screenshotDir = Join-Path $WorkspacePath "screenshots"

# Auto-cleanup: delete screenshots older than 15 days
if (-not $SkipCleanup) {
    if (Test-Path $screenshotDir) {
        $cutoffDate = (Get-Date).AddDays(-15)
        $oldFiles = Get-ChildItem $screenshotDir -Filter "*.png" | 
            Where-Object { $_.LastWriteTime -lt $cutoffDate }
        
        if ($oldFiles) {
            $deletedCount = 0
            $oldFiles | ForEach-Object { 
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
                $deletedCount++
            }
            Write-Output "[Cleanup] Deleted $deletedCount expired screenshot(s)"
        }
    }
}

# Ensure screenshot directory exists
if (-not (Test-Path $screenshotDir)) {
    New-Item -ItemType Directory -Path $screenshotDir -Force | Out-Null
}

# Default output path with timestamp
if ([string]::IsNullOrEmpty($OutputPath)) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputPath = Join-Path $screenshotDir "screenshot_$timestamp.png"
}

# Get screen bounds
if ($AllScreens) {
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
} else {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
}

# Create bitmap and capture
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)

# Save
$bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
$graphics.Dispose()

# Output result
Write-Output $OutputPath
