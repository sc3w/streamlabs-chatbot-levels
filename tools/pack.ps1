$sourceIdentifier = "StreamlabsChatbotLevelsWatcher"

$pwd = Get-Location
$watch_path = Join-Path $pwd "../src" -Resolve

$watcher = New-Object System.IO.FileSystemWatcher 
$watcher.Path = $watch_path
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$action = { 
    New-Item -ItemType Directory -Force -Path "../dist"

    $from = Join-Path $global:pwd "../src" -Resolve
    $to = Join-Path $global:pwd "../dist/Levels.zip"
    Write-Host $to
    Write-Host "Distribution package created @" $(Get-Date -Format "HH:mm:ss")
    Compress-Archive -Path $from -CompressionLevel Fastest -DestinationPath $to -Force
}    

Unregister-Event $sourceIdentifier -ErrorAction SilentlyContinue

$eventArgs = @{
    Input = $watcher
    EventName = "Changed"
    SourceIdentifier = $sourceIdentifier
    Action = $action
}

Register-ObjectEvent @eventArgs