param(
    [Parameter(Mandatory=$true)][string]$Registry,
    [string]$Tag = "latest"
)

$backendImage = "$Registry/rag-api:$Tag"
$frontendImage = "$Registry/rag-web:$Tag"

Write-Host "Building backend image $backendImage"
docker build -t $backendImage ./backend

Write-Host "Building frontend image $frontendImage"
docker build -t $frontendImage ./frontend

Write-Host "Pushing images"
docker push $backendImage
docker push $frontendImage

Write-Host "Done"
