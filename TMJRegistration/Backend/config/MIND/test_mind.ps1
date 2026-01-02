# ========================================
# MIND Feature Verification Script
# ========================================
# 用途：验证 MIND 算法是否产生模态独立的特征
# 
# 使用方法：
# .\test_mind.ps1 <fixed_image> <moving_image> <output_folder>
#
# 示例：
# cd config\MIND
# .\test_mind.ps1 ..\..\data\ct.nrrd ..\..\data\mri.nrrd ..\..\output\mind_test
# ========================================

param(
    [Parameter(Mandatory=$true)]
    [string]$FixedImage,
    
    [Parameter(Mandatory=$true)]
    [string]$MovingImage,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputPrefix,
    
    [int]$Radius = 1,
    [double]$Sigma = 0.8,
    [string]$Neighborhood = "6-connected"
)

$ErrorActionPreference = "Stop"

# 检查文件是否存在
if (-not (Test-Path $FixedImage)) {
    Write-Error "Fixed image not found: $FixedImage"
    exit 1
}

if (-not (Test-Path $MovingImage)) {
    Write-Error "Moving image not found: $MovingImage"
    exit 1
}

# 确保输出目录存在
$outputDir = Split-Path -Parent $OutputPrefix
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "[Created output directory: $outputDir]" -ForegroundColor Green
}

# 查找测试程序 (从 config/MIND 目录向上查找)
$testExe = "..\..\build\bin\Release\TestMINDSimple.exe"
if (-not (Test-Path $testExe)) {
    Write-Error "Test executable not found: $testExe"
    Write-Host "Please run build.ps1 first to compile the test program" -ForegroundColor Yellow
    Write-Host "Expected location: Backend\build\bin\Release\TestMINDSimple.exe" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MIND Feature Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Input:"
Write-Host "  Fixed:  $FixedImage"
Write-Host "  Moving: $MovingImage"
Write-Host "`nParameters:"
Write-Host "  Radius:       $Radius"
Write-Host "  Sigma:        $Sigma"
Write-Host "  Neighborhood: $Neighborhood"
Write-Host "`nOutput prefix: $OutputPrefix`n"

# 运行测试程序
Write-Host "Running MIND feature extraction...`n" -ForegroundColor Yellow

& $testExe $FixedImage $MovingImage $OutputPrefix --radius $Radius --sigma $Sigma --neighborhood $Neighborhood

if ($LASTEXITCODE -ne 0) {
    Write-Error "Test program failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Test Completed Successfully!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Generated files:" -ForegroundColor Cyan
Get-ChildItem "${OutputPrefix}*.nrrd" | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "  $($_.Name) (${size} MB)"
}

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Open 3D Slicer"
Write-Host "2. Load the output files:"
Write-Host "   - Original: $FixedImage and $MovingImage"
Write-Host "   - D_P images: ${OutputPrefix}_*_dp_ch*.nrrd (compare with paper Fig. 1)"
Write-Host "   - MIND features: ${OutputPrefix}_*_mind_ch*.nrrd"
Write-Host "3. Find a landmark (corner, edge) in both original images"
Write-Host "4. Check MIND descriptor values at that point across all 6 channels"
Write-Host "5. Compare fixed vs moving MIND values - they should be SIMILAR"
Write-Host "`nIf MIND descriptors are similar despite different modalities,"
Write-Host "then MIND is working correctly!`n" -ForegroundColor Green
