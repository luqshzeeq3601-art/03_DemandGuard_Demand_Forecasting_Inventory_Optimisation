# PowerShell Deployment helper script for GCP Cloud Run
param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "asia-southeast1",
    [string]$ServiceName = "demandguard-api",
    [string]$RepoName = "demandguard-repo",
    [string]$ImageTag = "latest"
)

if (-not $ProjectId) {
    Write-Warning "GCP_PROJECT_ID not set. Please provide -ProjectId parameter or set environment variable."
    exit 1
}

$ImageUri = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/${ServiceName}:${ImageTag}"

Write-Host "=== DemandGuard Cloud Run Deployment ===" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId"
Write-Host "Region:     $Region"
Write-Host "Image URI:  $ImageUri"

Write-Host "`nStep 1: Configuring Docker authentication..." -ForegroundColor Yellow
gcloud auth configure-docker "${Region}-docker.pkg.dev" --quiet

Write-Host "`nStep 2: Building and pushing Docker image..." -ForegroundColor Yellow
docker build -t $ImageUri .
docker push $ImageUri

Write-Host "`nStep 3: Deploying service to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image $ImageUri `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 2 `
    --port 8000

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
$ServiceUrl = gcloud run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)'
Write-Host "Live API Docs: $ServiceUrl/docs" -ForegroundColor Cyan
