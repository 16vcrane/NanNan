param(
  [switch]$SkipBackendTests,
  [switch]$SkipExternalChecks
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
  python -m compileall -q backend
  if ($LASTEXITCODE -ne 0) { throw 'Python syntax check failed' }

  node --check miniprogram\app.js
  node --check miniprogram\config\environment.js
  node --check miniprogram\services\api.js
  node --check miniprogram\utils\request.js
  if ($LASTEXITCODE -ne 0) { throw 'JavaScript syntax check failed' }

  $miniTests = Get-ChildItem tests\miniprogram\*.test.js | ForEach-Object FullName
  node --test $miniTests
  if ($LASTEXITCODE -ne 0) { throw 'Mini Program tests failed' }

  docker compose config --quiet
  if ($LASTEXITCODE -ne 0) { throw 'Development Compose config is invalid' }

  if (-not $SkipBackendTests) {
    $testMount = "${repoRoot}\backend\tests:/app/tests"
    docker compose run --rm -T -v $testMount backend pytest -q tests
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
  }

  git diff --check
  if ($LASTEXITCODE -ne 0) { throw 'Git whitespace check failed' }

  if (-not $SkipExternalChecks) {
    $environmentConfig = Get-Content miniprogram\config\environment.js -Raw
    if ($environmentConfig -match "PRODUCTION_API_BASE_URL = ''") {
      throw 'Set PRODUCTION_API_BASE_URL before release'
    }
    if (-not (Test-Path .env.production)) {
      throw 'Create .env.production before release'
    }
    docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Production Compose config is invalid' }
  }

  Write-Host 'Release checks passed.'
} finally {
  Pop-Location
}
