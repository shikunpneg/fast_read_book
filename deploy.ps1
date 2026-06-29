# 一键部署脚本：GitHub + PyPI
# 用法：先在浏览器创建 GitHub 空仓库 + 注册 PyPI 账号 + 生成 token，然后：
#   .\deploy.ps1 -GitHubToken "ghp_xxx" -PyPIToken "pypi-xxx"

param(
    [string]$GitHubUser = "shikunpneg",
    [string]$RepoName = "kg-book-tool",
    [string]$GitHubToken = "",
    [string]$PyPIToken = "",
    [switch]$SkipPyPI
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

Write-Host "=== kg-book-tool 部署脚本 ===" -ForegroundColor Cyan

# 1. GitHub
Write-Host "`n[1/3] 推送到 GitHub..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/$GitHubUser/$RepoName.git"
$pushUrl = if ($GitHubToken) { "https://$GitHubToken@github.com/$GitHubUser/$RepoName.git" } else { $remoteUrl }

git remote remove origin 2>$null
git remote add origin $pushUrl
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ GitHub 推送失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ GitHub 推送成功: $remoteUrl" -ForegroundColor Green

# 2. 构建包
Write-Host "`n[2/3] 构建分发包..." -ForegroundColor Yellow
python -m pip install --upgrade build twine --quiet
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 构建完成" -ForegroundColor Green

# 3. PyPI
if (-not $SkipPyPI) {
    Write-Host "`n[3/3] 上传到 PyPI..." -ForegroundColor Yellow
    if (-not $PyPIToken) {
        Write-Host "未提供 -PyPIToken，跳过 PyPI 上传" -ForegroundColor DarkYellow
        Write-Host "可手动执行: twine upload dist/*" -ForegroundColor DarkYellow
    } else {
        $env:TWINE_USERNAME = "__token__"
        $env:TWINE_PASSWORD = $PyPIToken
        twine upload dist/*
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ PyPI 上传失败" -ForegroundColor Red
            exit 1
        }
        Write-Host "✓ PyPI 上传成功: https://pypi.org/project/$RepoName/" -ForegroundColor Green
    }
}

Write-Host "`n=== 完成 ===" -ForegroundColor Cyan
Write-Host "GitHub: https://github.com/$GitHubUser/$RepoName"
if (-not $SkipPyPI) {
    Write-Host "PyPI:   https://pypi.org/project/$RepoName/"
}
