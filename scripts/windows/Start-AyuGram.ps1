param(
    [string]$ContainerName = "ayugram-dev-ui",
    [string]$NoVncUrl = "http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale",
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$FailureMessage
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (& $Condition) {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw $FailureMessage
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI não foi encontrado no PATH."
}

$container = docker ps -a --filter "name=^/${ContainerName}$" --format "{{.Names}}" | Select-Object -First 1
if ($container -ne $ContainerName) {
    throw "Container '$ContainerName' não existe. Certifique-se de iniciar o devcontainer primeiro."
}

$running = docker inspect --format "{{.State.Running}}" $ContainerName
if ($running -ne "true") {
    Write-Host "Iniciando container $ContainerName..."
    docker start $ContainerName | Out-Null
}

Write-Host "Aguardando container ficar ready..."
Wait-Until -TimeoutSeconds $TimeoutSeconds -FailureMessage "O container não atingiu o estado running." -Condition {
    (docker inspect --format "{{.State.Running}}" $ContainerName 2>$null) -eq "true"
}

Write-Host "Verificando processo AyuGram..."
$processCheck = docker exec $ContainerName bash -lc 'pgrep -x AyuGram >/dev/null; echo $?'
if ($processCheck -ne "0") {
    Write-Host "Iniciando launcher do AyuGram dentro do container..."
    docker exec $ContainerName bash -lc '
        set -e
        export DISPLAY=:1
        export LIBGL_ALWAYS_SOFTWARE=1
        export QT_X11_NO_MITSHM=1
        cd /usr/src/tdesktop
        nohup .devcontainer/launch-ayugram.sh >/tmp/ayugram-runtime.log 2>&1 &
    '
}

Write-Host "Aguardando inicialização do processo..."
Wait-Until -TimeoutSeconds $TimeoutSeconds -FailureMessage "O processo AyuGram não permaneceu ativo." -Condition {
    $check = docker exec $ContainerName bash -lc 'pgrep -x AyuGram >/dev/null; echo $?'
    $check -eq "0"
}

Write-Host "Aguardando janela X11 ser renderizada..."
Wait-Until -TimeoutSeconds $TimeoutSeconds -FailureMessage "A janela do AyuGram não foi encontrada no display X11." -Condition {
    docker exec $ContainerName bash -lc 'DISPLAY=:1 wmctrl -lx | grep -iE "AyuGram|Telegram" >/dev/null 2>&1'
    $LASTEXITCODE -eq 0
}

Write-Host "Aguardando socket 6080 (noVNC)..."
Wait-Until -TimeoutSeconds $TimeoutSeconds -FailureMessage "A porta 6080 não ficou disponível." -Condition {
    (Test-NetConnection -ComputerName 127.0.0.1 -Port 6080 -WarningAction SilentlyContinue).TcpTestSucceeded
}

$VncPassword = (docker exec $ContainerName cat /home/user/.local/state/ayugram-desktop/password).Trim()

Write-Host "Ambiente pronto! Abrindo navegador..."
Start-Process "$NoVncUrl&password=$VncPassword"
