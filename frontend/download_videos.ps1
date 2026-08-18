# Zarkaan Traffic Surveillance - Video Downloader
# Downloads free traffic surveillance footage from Pixabay (Pixabay License - free for commercial use)
# Run this script from the project root or frontend directory

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  ZARKAAN VIDEO ASSET DOWNLOADER" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Determine the correct video directory path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$videoDir = Join-Path $scriptDir "assets\videos"

# Create directory if it doesn't exist
if (-Not (Test-Path $videoDir)) {
    New-Item -ItemType Directory -Path $videoDir -Force | Out-Null
    Write-Host "[+] Created directory: $videoDir" -ForegroundColor Green
}

# Pixabay free traffic videos (Pixabay License - free for commercial and non-commercial use)
$videos = @(
    @{
        Name = "traffic_main.mp4"
        Url = "https://cdn.pixabay.com/video/2019/03/13/21985-323496013_large.mp4"
        Description = "Main camera - Traffic intersection view"
    },
    @{
        Name = "traffic_cam2.mp4"
        Url = "https://cdn.pixabay.com/video/2023/09/13/180386-864121573_large.mp4"
        Description = "CAM-02 - City traffic flow"
    },
    @{
        Name = "traffic_cam3.mp4"
        Url = "https://cdn.pixabay.com/video/2018/11/29/19627-304735769_large.mp4"
        Description = "CAM-03 - Highway traffic"
    },
    @{
        Name = "traffic_cam4.mp4"
        Url = "https://cdn.pixabay.com/video/2022/11/22/140078-774032962_large.mp4"
        Description = "CAM-04 - Night traffic"
    },
    @{
        Name = "traffic_cam5.mp4"
        Url = "https://cdn.pixabay.com/video/2019/05/01/23232-333604632_large.mp4"
        Description = "CAM-05 - Busy intersection"
    }
)

$downloadCount = 0
$ProgressPreference = 'SilentlyContinue'

foreach ($video in $videos) {
    $filePath = Join-Path $videoDir $video.Name
    
    if (Test-Path $filePath) {
        $size = [math]::Round((Get-Item $filePath).Length / 1MB, 2)
        Write-Host "  [SKIP] $($video.Name) already exists ($size MB)" -ForegroundColor Yellow
        continue
    }

    Write-Host ""
    Write-Host "  Downloading: $($video.Description)..." -ForegroundColor White
    Write-Host "  URL: $($video.Url)" -ForegroundColor DarkGray
    
    try {
        Invoke-WebRequest -Uri $video.Url -OutFile $filePath -UseBasicParsing -TimeoutSec 120
        $size = [math]::Round((Get-Item $filePath).Length / 1MB, 2)
        Write-Host "  [OK] Downloaded $($video.Name) ($size MB)" -ForegroundColor Green
        $downloadCount++
    }
    catch {
        Write-Host "  [FAIL] Could not download: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Manual alternative:" -ForegroundColor Yellow
        Write-Host "  1. Open this URL in your browser: $($video.Url)" -ForegroundColor Gray
        Write-Host "  2. Save the file as: $filePath" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Done! $downloadCount new videos downloaded." -ForegroundColor Cyan
Write-Host "  Location: $videoDir" -ForegroundColor Gray
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

if ($downloadCount -lt $videos.Count) {
    $existing = (Get-ChildItem $videoDir -Filter "*.mp4" -ErrorAction SilentlyContinue).Count
    Write-Host "  $existing / $($videos.Count) videos available locally." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  NOTE: The dashboard will automatically use Pixabay CDN" -ForegroundColor Gray
    Write-Host "  as fallback if local videos are missing. But for best" -ForegroundColor Gray
    Write-Host "  performance and offline use, download all videos locally." -ForegroundColor Gray
}

Write-Host ""
