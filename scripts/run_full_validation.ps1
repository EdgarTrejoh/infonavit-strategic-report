param(
    [bool]$IncludeTests = $true,
    [bool]$IncludeLocalDbHealth = $true,
    [bool]$IncludeMigrationCheck = $true,
    [switch]$RunLocalMigration,
    [bool]$IncludeMain = $true,
    [bool]$IncludeLocalApi = $true,
    [bool]$IncludeLocalEndpoints = $true,
    [bool]$IncludeAI = $true,
    [bool]$IncludeSupabaseHealth = $true,
    [bool]$IncludeCloudRun = $true,
    [int]$LocalApiPort = 8010,
    [string]$CloudRunBaseUrl = "https://infonavit-strategic-report-api-490229283844.us-west1.run.app",
    [int]$TimeoutSeconds = 60,
    [switch]$SkipTests,
    [switch]$SkipLocalDbHealth,
    [switch]$SkipMigrationCheck,
    [switch]$SkipMain,
    [switch]$SkipLocalApi,
    [switch]$SkipLocalEndpoints,
    [switch]$SkipAI,
    [switch]$SkipSupabaseHealth,
    [switch]$SkipCloudRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$RunId = Get-Date -Format "yyyyMMdd_HHmmss"
$StartedAt = Get-Date
$ReportDir = Join-Path $ProjectRoot "outputs\validation"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

$MarkdownReport = Join-Path $ReportDir "full_validation_$RunId.md"
$JsonReport = Join-Path $ReportDir "full_validation_$RunId.json"
$UvicornStdoutLog = Join-Path $ReportDir "uvicorn_$RunId.out.log"
$UvicornStderrLog = Join-Path $ReportDir "uvicorn_$RunId.err.log"

$Results = New-Object System.Collections.Generic.List[object]
$LocalApiProcess = $null
$StartedLocalApi = $false

function Get-PythonExe {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        try {
            & $venvPython --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $venvPython
            }
        } catch {
            # Continue with other candidates.
        }
    }
    foreach ($candidate in @("python", "py")) {
        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            # Continue with other candidates.
        }
    }
    return "python"
}

function Get-ShortText {
    param(
        [AllowNull()][object]$Value,
        [int]$MaxLength = 1200
    )
    if ($null -eq $Value) {
        return ""
    }
    $text = ($Value | Out-String).Trim()
    if ($text.Length -le $MaxLength) {
        return $text
    }
    return $text.Substring(0, $MaxLength) + "... [truncated]"
}

function Remove-SensitiveText {
    param([AllowNull()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $Text
    }
    $sanitized = $Text
    $sensitiveNames = @(
        "DATABASE_URL",
        "DATABASE_URL_READONLY",
        "DB_PASSWORD",
        "INFONAVIT_API_KEY",
        "OPENAI_API_KEY",
        "INFLACION_COPILOT_URL"
    )
    foreach ($name in $sensitiveNames) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $sanitized = $sanitized.Replace($value, "[REDACTED:$name]")
        }
    }
    $sanitized = $sanitized -replace "postgresql\+psycopg2://[^ \r\n]+", "[REDACTED:DATABASE_URL]"
    $sanitized = $sanitized -replace "postgresql://[^ \r\n]+", "[REDACTED:DATABASE_URL]"
    return $sanitized
}

function Add-Result {
    param(
        [string]$Name,
        [ValidateSet("ok", "error", "skipped")][string]$Status,
        [int]$DurationMs = 0,
        [AllowNull()][int]$ExitCode = $null,
        [string]$Message = "",
        [AllowNull()][object]$Details = $null
    )
    $Results.Add([ordered]@{
        name = $Name
        status = $Status
        duration_ms = $DurationMs
        exit_code = $ExitCode
        message = Remove-SensitiveText (Get-ShortText $Message)
        details = Remove-SensitiveText (Get-ShortText $Details)
    }) | Out-Null
}

function Import-DotEnv {
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        Add-Result -Name "load .env" -Status "skipped" -Message ".env no existe; se usaran variables ya cargadas en la sesion."
        return
    }

    $loaded = 0
    foreach ($line in Get-Content $envPath) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ([string]::IsNullOrWhiteSpace($key)) {
            continue
        }
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($key, "Process"))) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            $loaded += 1
        }
    }
    Add-Result -Name "load .env" -Status "ok" -Message "Variables cargadas sin imprimir valores." -Details "variables_loaded=$loaded"
}

function Invoke-CommandStep {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$ExpectedExitCode = 0
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        $sw.Stop()
        if ($exitCode -eq $ExpectedExitCode) {
            Add-Result -Name $Name -Status "ok" -DurationMs $sw.ElapsedMilliseconds -ExitCode $exitCode -Message "Comando finalizado correctamente." -Details $output
        } else {
            Add-Result -Name $Name -Status "error" -DurationMs $sw.ElapsedMilliseconds -ExitCode $exitCode -Message "Exit code inesperado." -Details $output
        }
    } catch {
        $sw.Stop()
        Add-Result -Name $Name -Status "error" -DurationMs $sw.ElapsedMilliseconds -Message $_.Exception.GetType().Name -Details $_.Exception.Message
    }
}

function Invoke-PythonCodeStep {
    param(
        [string]$Name,
        [string]$Code
    )
    Invoke-CommandStep -Name $Name -FilePath $PythonExe -Arguments @("-c", $Code)
}

function Invoke-HttpStep {
    param(
        [string]$Name,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [string]$ExpectedContains = "",
        [switch]$PlainText
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-RestMethod -Uri $Uri -Method Get -Headers $Headers -TimeoutSec $TimeoutSeconds
        $sw.Stop()
        $text = if ($PlainText) { [string]$response } else { $response | ConvertTo-Json -Depth 8 }
        if (-not [string]::IsNullOrWhiteSpace($ExpectedContains) -and ($text -notlike "*$ExpectedContains*")) {
            Add-Result -Name $Name -Status "error" -DurationMs $sw.ElapsedMilliseconds -Message "La respuesta no contiene el texto esperado." -Details $text
            return
        }
        $summary = if ($PlainText) {
            "length=$($text.Length)"
        } else {
            Get-ShortText $text 700
        }
        Add-Result -Name $Name -Status "ok" -DurationMs $sw.ElapsedMilliseconds -Message "HTTP OK." -Details $summary
    } catch {
        $sw.Stop()
        $message = $_.Exception.Message
        Add-Result -Name $Name -Status "error" -DurationMs $sw.ElapsedMilliseconds -Message $_.Exception.GetType().Name -Details $message
    }
}

function Test-UrlReady {
    param([string]$Uri)
    try {
        Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-ApiHeaders {
    $apiKey = [Environment]::GetEnvironmentVariable("INFONAVIT_API_KEY", "Process")
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        return $null
    }
    return @{ "X-API-Key" = $apiKey }
}

function Invoke-ProtectedEndpoint {
    param(
        [string]$Name,
        [string]$Uri,
        [switch]$PlainText
    )
    $headers = Get-ApiHeaders
    if ($null -eq $headers) {
        Add-Result -Name $Name -Status "skipped" -Message "INFONAVIT_API_KEY no esta configurada en el entorno."
        return
    }
    Invoke-HttpStep -Name $Name -Uri $Uri -Headers $headers -PlainText:$PlainText
}

function Get-ResultStatus {
    param([object]$Item)
    if ($Item -is [System.Collections.IDictionary]) {
        return [string]$Item["status"]
    }
    return [string]$Item.status
}

function Get-ResultStatusCount {
    param([string]$Status)
    $count = 0
    for ($i = 0; $i -lt $Results.Count; $i++) {
        $item = $Results[$i]
        if ((Get-ResultStatus $item) -eq $Status) {
            $count += 1
        }
    }
    return $count
}

function Add-LocalEndpointSkippedResults {
    param([string]$Message)
    foreach ($name in @(
        "local /health",
        "local /db/health",
        "local /diagnostics/db-metrics",
        "local /mini-report/extended/json",
        "local /mini-report/extended/markdown",
        "local /mini-report/ai/json",
        "local /mini-report/ai/markdown"
    )) {
        Add-Result -Name $name -Status "skipped" -Message $Message
    }
}

function Add-CloudRunEndpointSkippedResults {
    param([string]$Message)
    foreach ($name in @(
        "Cloud Run /health",
        "Cloud Run /db/health",
        "Cloud Run /diagnostics/db-metrics",
        "Cloud Run /mini-report/extended/json",
        "Cloud Run /mini-report/extended/markdown",
        "Cloud Run /mini-report/ai/json",
        "Cloud Run /mini-report/ai/markdown"
    )) {
        Add-Result -Name $name -Status "skipped" -Message $Message
    }
}

function Write-Reports {
    $finishedAt = Get-Date
    $summary = [ordered]@{
        ok = Get-ResultStatusCount "ok"
        error = Get-ResultStatusCount "error"
        skipped = Get-ResultStatusCount "skipped"
    }
    $payload = [ordered]@{
        run_id = $RunId
        started_at = $StartedAt.ToString("s")
        finished_at = $finishedAt.ToString("s")
        project_root = [string]$ProjectRoot
        python_exe = [string]$PythonExe
        cloud_run_base_url = $CloudRunBaseUrl
        summary = $summary
        results = $Results
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -Path $JsonReport -Encoding UTF8

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Full Validation Report - INFONAVIT Strategic Report") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add(('- Run ID: `{0}`' -f $RunId)) | Out-Null
    $lines.Add(('- Started at: `{0}`' -f $StartedAt.ToString("s"))) | Out-Null
    $lines.Add(('- Finished at: `{0}`' -f $finishedAt.ToString("s"))) | Out-Null
    $lines.Add(('- Project root: `{0}`' -f $ProjectRoot)) | Out-Null
    $lines.Add(('- Python: `{0}`' -f $PythonExe)) | Out-Null
    $lines.Add(('- JSON report: `{0}`' -f $JsonReport)) | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("## Summary") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("- OK: $($summary.ok)") | Out-Null
    $lines.Add("- Error: $($summary.error)") | Out-Null
    $lines.Add("- Skipped: $($summary.skipped)") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("## Results") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("| Step | Status | Duration ms | Message |") | Out-Null
    $lines.Add("| --- | --- | ---: | --- |") | Out-Null
    foreach ($item in $Results) {
        $name = if ($item -is [System.Collections.IDictionary]) { $item["name"] } else { $item.name }
        $status = Get-ResultStatus $item
        $duration = if ($item -is [System.Collections.IDictionary]) { $item["duration_ms"] } else { $item.duration_ms }
        $rawMessage = if ($item -is [System.Collections.IDictionary]) { $item["message"] } else { $item.message }
        $message = ($rawMessage -replace "\|", "\|") -replace "`r?`n", " "
        $lines.Add("| $name | $status | $duration | $message |") | Out-Null
    }
    $lines.Add("") | Out-Null
    $lines.Add("## Notes") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("- La migracion real solo se ejecuta si se pasa `-RunLocalMigration`.") | Out-Null
    $lines.Add("- El reporte intenta sanitizar secretos conocidos y no imprime valores de `.env`.") | Out-Null
    $lines.Add("- Los endpoints protegidos se omiten si `INFONAVIT_API_KEY` no esta configurada.") | Out-Null
    $lines.Add("- Los endpoints IA locales se omiten si `OPENAI_API_KEY` no esta configurada.") | Out-Null
    $lines | Set-Content -Path $MarkdownReport -Encoding UTF8

    Write-Host "Reporte Markdown: $MarkdownReport"
    Write-Host "Reporte JSON: $JsonReport"
    Write-Host "Resumen: ok=$($summary.ok) error=$($summary.error) skipped=$($summary.skipped)"
}

$PythonExe = Get-PythonExe

if ($SkipTests) { $IncludeTests = $false }
if ($SkipLocalDbHealth) { $IncludeLocalDbHealth = $false }
if ($SkipMigrationCheck) { $IncludeMigrationCheck = $false }
if ($SkipMain) { $IncludeMain = $false }
if ($SkipLocalApi) { $IncludeLocalApi = $false }
if ($SkipLocalEndpoints) { $IncludeLocalEndpoints = $false }
if ($SkipAI) { $IncludeAI = $false }
if ($SkipSupabaseHealth) { $IncludeSupabaseHealth = $false }
if ($SkipCloudRun) { $IncludeCloudRun = $false }

try {
    Import-DotEnv

    if ($IncludeTests) {
        Invoke-CommandStep -Name "pytest" -FilePath $PythonExe -Arguments @("-m", "pytest", "-q")
    } else {
        Add-Result -Name "pytest" -Status "skipped" -Message "IncludeTests=false"
    }

    if ($IncludeLocalDbHealth) {
        Invoke-PythonCodeStep -Name "local database health_check" -Code "from database import health_check; ok,msg=health_check(); print('ok=' + str(ok)); print('message=' + str(msg))"
    } else {
        Add-Result -Name "local database health_check" -Status "skipped" -Message "IncludeLocalDbHealth=false"
    }

    if ($IncludeSupabaseHealth) {
        $readonlyUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL_READONLY", "Process")
        if ([string]::IsNullOrWhiteSpace($readonlyUrl)) {
            Add-Result -Name "Supabase read-only health_check" -Status "skipped" -Message "DATABASE_URL_READONLY no esta configurada."
        } else {
            $previousDatabaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
            [Environment]::SetEnvironmentVariable("DATABASE_URL", $readonlyUrl, "Process")
            Invoke-PythonCodeStep -Name "Supabase read-only health_check" -Code "from database import health_check; ok,msg=health_check(); print('ok=' + str(ok)); print('message=' + str(msg))"
            [Environment]::SetEnvironmentVariable("DATABASE_URL", $previousDatabaseUrl, "Process")
        }
    } else {
        Add-Result -Name "Supabase read-only health_check" -Status "skipped" -Message "IncludeSupabaseHealth=false"
    }

    if ($IncludeMigrationCheck) {
        Invoke-CommandStep -Name "migration CLI safety check" -FilePath $PythonExe -Arguments @("migrate_csv_to_pg.py", "--help")
        if ($RunLocalMigration) {
            Invoke-CommandStep -Name "local migration run" -FilePath $PythonExe -Arguments @("migrate_csv_to_pg.py", "--run", "--yes")
        } else {
            Add-Result -Name "local migration run" -Status "skipped" -Message "Migracion real omitida. Usar -RunLocalMigration para ejecutarla."
        }
    } else {
        Add-Result -Name "migration CLI safety check" -Status "skipped" -Message "IncludeMigrationCheck=false"
    }

    if ($IncludeMain) {
        Invoke-CommandStep -Name "main.py" -FilePath $PythonExe -Arguments @("main.py")
    } else {
        Add-Result -Name "main.py" -Status "skipped" -Message "IncludeMain=false"
    }

    $localBaseUrl = "http://127.0.0.1:$LocalApiPort"
    $localApiAvailable = $false
    if ($IncludeLocalApi) {
        try {
            if (Test-UrlReady "$localBaseUrl/health") {
                $localApiAvailable = $true
                Add-Result -Name "local API start" -Status "ok" -Message "API local ya estaba respondiendo en $localBaseUrl."
            } else {
                $uvicornArgs = @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "$LocalApiPort")
                $LocalApiProcess = Start-Process -FilePath $PythonExe -ArgumentList $uvicornArgs -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $UvicornStdoutLog -RedirectStandardError $UvicornStderrLog
                $StartedLocalApi = $true
                $ready = $false
                $waitSw = [System.Diagnostics.Stopwatch]::StartNew()
                while ($waitSw.Elapsed.TotalSeconds -lt 30) {
                    if (Test-UrlReady "$localBaseUrl/health") {
                        $ready = $true
                        break
                    }
                    Start-Sleep -Milliseconds 800
                }
                $waitSw.Stop()
                if ($ready) {
                    $localApiAvailable = $true
                    Add-Result -Name "local API start" -Status "ok" -DurationMs $waitSw.ElapsedMilliseconds -Message "API local iniciada en $localBaseUrl." -Details "stdout=$UvicornStdoutLog; stderr=$UvicornStderrLog"
                } else {
                    Add-Result -Name "local API start" -Status "error" -DurationMs $waitSw.ElapsedMilliseconds -Message "API local no respondio a tiempo." -Details "stdout=$UvicornStdoutLog; stderr=$UvicornStderrLog"
                }
            }
        } catch {
            Add-Result -Name "local API start" -Status "error" -Message $_.Exception.GetType().Name -Details $_.Exception.Message
        }
    } else {
        Add-Result -Name "local API start" -Status "skipped" -Message "IncludeLocalApi=false"
    }

    if ($IncludeLocalEndpoints) {
        if (-not $localApiAvailable) {
            Add-LocalEndpointSkippedResults -Message "API local no disponible; no se probaron endpoints locales."
        } else {
            Invoke-HttpStep -Name "local /health" -Uri "$localBaseUrl/health"
            Invoke-ProtectedEndpoint -Name "local /db/health" -Uri "$localBaseUrl/db/health"
            Invoke-ProtectedEndpoint -Name "local /diagnostics/db-metrics" -Uri "$localBaseUrl/diagnostics/db-metrics?start_year=2025&end_year=2026"
            Invoke-ProtectedEndpoint -Name "local /mini-report/extended/json" -Uri "$localBaseUrl/mini-report/extended/json?current_year=2026&previous_year=2025&month_limit=4"
            Invoke-ProtectedEndpoint -Name "local /mini-report/extended/markdown" -Uri "$localBaseUrl/mini-report/extended/markdown?current_year=2026&previous_year=2025&month_limit=4" -PlainText
            if ($IncludeAI) {
                if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "Process"))) {
                    Add-Result -Name "local /mini-report/ai/json" -Status "skipped" -Message "OPENAI_API_KEY no esta configurada para prueba local con IA."
                    Add-Result -Name "local /mini-report/ai/markdown" -Status "skipped" -Message "OPENAI_API_KEY no esta configurada para prueba local con IA."
                } else {
                    Invoke-ProtectedEndpoint -Name "local /mini-report/ai/json" -Uri "$localBaseUrl/mini-report/ai/json?current_year=2026&previous_year=2025&month_limit=4"
                    Invoke-ProtectedEndpoint -Name "local /mini-report/ai/markdown" -Uri "$localBaseUrl/mini-report/ai/markdown?current_year=2026&previous_year=2025&month_limit=4" -PlainText
                }
            } else {
                Add-Result -Name "local /mini-report/ai/json" -Status "skipped" -Message "IncludeAI=false"
                Add-Result -Name "local /mini-report/ai/markdown" -Status "skipped" -Message "IncludeAI=false"
            }
        }
    } else {
        Add-LocalEndpointSkippedResults -Message "IncludeLocalEndpoints=false"
    }

    if ($IncludeCloudRun) {
        $cloudBase = $CloudRunBaseUrl.TrimEnd("/")
        Invoke-HttpStep -Name "Cloud Run /health" -Uri "$cloudBase/health"
        Invoke-ProtectedEndpoint -Name "Cloud Run /db/health" -Uri "$cloudBase/db/health"
        Invoke-ProtectedEndpoint -Name "Cloud Run /diagnostics/db-metrics" -Uri "$cloudBase/diagnostics/db-metrics?start_year=2025&end_year=2026"
        Invoke-ProtectedEndpoint -Name "Cloud Run /mini-report/extended/json" -Uri "$cloudBase/mini-report/extended/json?current_year=2026&previous_year=2025&month_limit=4"
        Invoke-ProtectedEndpoint -Name "Cloud Run /mini-report/extended/markdown" -Uri "$cloudBase/mini-report/extended/markdown?current_year=2026&previous_year=2025&month_limit=4" -PlainText
        if ($IncludeAI) {
            Invoke-ProtectedEndpoint -Name "Cloud Run /mini-report/ai/json" -Uri "$cloudBase/mini-report/ai/json?current_year=2026&previous_year=2025&month_limit=4"
            Invoke-ProtectedEndpoint -Name "Cloud Run /mini-report/ai/markdown" -Uri "$cloudBase/mini-report/ai/markdown?current_year=2026&previous_year=2025&month_limit=4" -PlainText
        } else {
            Add-Result -Name "Cloud Run /mini-report/ai/json" -Status "skipped" -Message "IncludeAI=false"
            Add-Result -Name "Cloud Run /mini-report/ai/markdown" -Status "skipped" -Message "IncludeAI=false"
        }
    } else {
        Add-CloudRunEndpointSkippedResults -Message "IncludeCloudRun=false"
    }
} finally {
    if ($StartedLocalApi -and $null -ne $LocalApiProcess -and -not $LocalApiProcess.HasExited) {
        Stop-Process -Id $LocalApiProcess.Id -Force
        Add-Result -Name "local API stop" -Status "ok" -Message "Proceso uvicorn detenido." -Details "pid=$($LocalApiProcess.Id)"
    }
    Write-Reports
}

$errorCount = Get-ResultStatusCount "error"
if ($errorCount -gt 0) {
    exit 1
}
exit 0
