$env:MXTERM_HOOK_ACTIVE = "1"
$env:MXTERM_HOOK_SHELL = "powershell"
$env:MXTERM_HOOK_AUTO_CAPTURE = "__MXTERM_AUTO_CAPTURE__"
$env:MXTERM_HOOK_AUTO_CAPTURE_MODE = "__MXTERM_AUTO_CAPTURE_MODE__"
$env:MXTERM_HOOK_EXPLICIT_COMMAND = "__MXTERM_EXPLICIT_COMMAND__"
$env:MXTERM_HOOK_ENTER_HANDLER = "0"
$env:MXTERM_HOOK_MODEL = "__MXTERM_MODEL__"

function Test-MXTermLooksNaturalLanguage {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return $false
    }

    if ($Line -match '[^\u0000-\u007F]') {
        return $true
    }

    $normalized = $Line.Trim().ToLowerInvariant()
    if ($normalized -match '\?') {
        return $true
    }

    return $normalized -match '^(please|help|show|find|list|install|start|stop|open|why|how|create|remove|delete|enter|go to|switch to)\b'
}

function Test-MXTermShouldAutoCapture {
    param([string]$Line)

    $mode = "$env:MXTERM_HOOK_AUTO_CAPTURE_MODE".Trim().ToLowerInvariant()
    if ($mode -eq "always") {
        return $true
    }

    if (Test-MXTermLooksNaturalLanguage -Line $Line) {
        return $true
    }

    if ($mode -eq "natural_language") {
        return $false
    }

    return $Line -match '\s'
}

function Get-MXTermFirstToken {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return ""
    }

    $trimmed = $Line.TrimStart()
    $parts = $trimmed -split '\s+', 2
    return $parts[0]
}

function Test-MXTermShellResolvesToken {
    param([string]$Token)

    if ([string]::IsNullOrWhiteSpace($Token)) {
        return $false
    }

    return $null -ne (Get-Command $Token -ErrorAction SilentlyContinue)
}

function Get-MXTermSpinnerFrames {
    return @('|', '/', '-', '.')
}

function Get-MXTermConfiguredModel {
    param([string]$MxtermExe = "")

    $fallback = "$env:MXTERM_HOOK_MODEL"
    if ([string]::IsNullOrWhiteSpace($fallback)) {
        $fallback = "unknown"
    }

    $resolvedExe = $MxtermExe
    if ([string]::IsNullOrWhiteSpace($resolvedExe)) {
        $command = Get-Command mxterm -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            $resolvedExe = $command.Source
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedExe)) {
        return $fallback
    }

    try {
        $resolvedModel = (& $resolvedExe model current 2>$null | Select-Object -First 1).Trim()
    } catch {
        $resolvedModel = ""
    }

    if ([string]::IsNullOrWhiteSpace($resolvedModel)) {
        return $fallback
    }

    return $resolvedModel
}

function Get-MXTermDecisionModel {
    param([object]$Decision)

    if ($null -ne $Decision -and $null -ne $Decision.PSObject.Properties["resolved_model"]) {
        $resolvedModel = [string]$Decision.resolved_model
        if (-not [string]::IsNullOrWhiteSpace($resolvedModel)) {
            return $resolvedModel
        }
    }

    return Get-MXTermConfiguredModel
}

function Write-MXTermStatus {
    param(
        [string]$Kind,
        [string]$Message
    )

    $color = switch ($Kind) {
        "success" { "Green" }
        "warning" { "Yellow" }
        "failure" { "Red" }
        default { "Cyan" }
    }

    Write-Host "o " -ForegroundColor $color -NoNewline
    Write-Host "MXTerm $([char]::ToUpper($Kind[0]) + $Kind.Substring(1))" -ForegroundColor $color -NoNewline
    Write-Host " | " -ForegroundColor DarkGray -NoNewline
    Write-Host $Message
}

function Show-MXTermDecision {
    param([object]$Decision)

    $kind = "success"
    $modelName = Get-MXTermDecisionModel -Decision $Decision
    if ($Decision.route -eq "block") {
        if ($Decision.message -like "*Please enter another request*") {
            $kind = "warning"
        } else {
            $kind = "failure"
        }
    } elseif ($Decision.route -eq "suggest_fix" -or $Decision.requires_confirmation -or $Decision.risk -in @("medium", "high")) {
        $kind = "warning"
    }

    Write-MXTermStatus -Kind $kind -Message $Decision.message

    $detailColor = "DarkCyan"
    if ($Decision.source -eq "ai") {
        Write-Host "model " -ForegroundColor $detailColor -NoNewline
        Write-Host $modelName -ForegroundColor White -NoNewline
        if (-not [string]::IsNullOrWhiteSpace($Decision.display_command)) {
            Write-Host "  |  " -ForegroundColor DarkGray -NoNewline
            Write-Host "command " -ForegroundColor $detailColor -NoNewline
            Write-Host $Decision.display_command -ForegroundColor White
        } else {
            Write-Host
        }
    } elseif ($Decision.source -eq "agent") {
        Write-Host "model " -ForegroundColor $detailColor -NoNewline
        Write-Host $modelName -ForegroundColor White -NoNewline
        if (-not [string]::IsNullOrWhiteSpace($Decision.display_command)) {
            Write-Host "  |  " -ForegroundColor DarkGray -NoNewline
            Write-Host "command " -ForegroundColor $detailColor -NoNewline
            Write-Host $Decision.display_command -ForegroundColor White
        } else {
            Write-Host
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($Decision.display_command)) {
        Write-Host "command " -ForegroundColor $detailColor -NoNewline
        Write-Host $Decision.display_command -ForegroundColor White
    }

    if ($kind -eq "success") {
        if (-not [string]::IsNullOrWhiteSpace($Decision.intent)) {
            Write-Host $Decision.intent -ForegroundColor DarkGray
        }
        return
    }

    Write-Host "input " -ForegroundColor $detailColor -NoNewline
    Write-Host $Decision.original_input -ForegroundColor White

    if (-not [string]::IsNullOrWhiteSpace($Decision.plan_summary)) {
        Write-Host "plan " -ForegroundColor $detailColor -NoNewline
        Write-Host $Decision.plan_summary -ForegroundColor Gray
    }

    if (-not [string]::IsNullOrWhiteSpace($Decision.explanation)) {
        Write-Host "intent " -ForegroundColor $detailColor -NoNewline
        Write-Host $Decision.intent -ForegroundColor White -NoNewline
        Write-Host " | " -ForegroundColor DarkGray -NoNewline
        Write-Host $Decision.explanation -ForegroundColor Gray
    }

    if (-not [string]::IsNullOrWhiteSpace($Decision.preview_summary)) {
        Write-Host "preview " -ForegroundColor Yellow -NoNewline
        Write-Host $Decision.preview_summary -ForegroundColor Gray
    }

    if ($Decision.preview_items) {
        foreach ($item in $Decision.preview_items) {
            Write-Host "  - $item" -ForegroundColor DarkGray
        }
    }

    if ([string]::IsNullOrWhiteSpace($Decision.display_command) -and $Decision.source -eq "ai") {
        Write-Host "warning " -ForegroundColor Yellow -NoNewline
        Write-Host "no executable command returned. Please enter another request." -ForegroundColor Gray
    }
}

function Invoke-MXTermResolve {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return $null
    }

    $mxtermExe = (Get-Command mxterm -ErrorAction SilentlyContinue).Source
    if ([string]::IsNullOrWhiteSpace($mxtermExe)) {
        Write-MXTermStatus -Kind failure -Message "mxterm is not available on PATH."
        return $null
    }

    $modelName = Get-MXTermConfiguredModel -MxtermExe $mxtermExe
    $job = Start-Job -ScriptBlock {
        param($Exe, $CurrentPath, $CurrentLine)
        & $Exe resolve --shell powershell --cwd $CurrentPath --input $CurrentLine --json 2>$null
    } -ArgumentList $mxtermExe, (Get-Location).Path, $Line

    $frames = Get-MXTermSpinnerFrames
    $index = 0
    while ($job.State -eq "Running") {
        $frame = $frames[$index % $frames.Count]
        Write-Host "`r$frame MXTerm translating with $modelName ..." -ForegroundColor Cyan -NoNewline
        Start-Sleep -Milliseconds 90
        $index++
        $job = Get-Job -Id $job.Id
    }
    Write-Host "`r$(' ' * 100)`r" -NoNewline

    $json = Receive-Job -Job $job -Wait
    $exitCode = $job.ChildJobs[0].JobStateInfo.State
    Remove-Job -Job $job -Force | Out-Null

    if ([string]::IsNullOrWhiteSpace($json)) {
        Write-MXTermStatus -Kind failure -Message "MXTerm did not return a decision."
        return $null
    }

    try {
        $decision = $json | ConvertFrom-Json
        $decision | Add-Member -NotePropertyName resolved_model -NotePropertyValue $modelName -Force
        return $decision
    } catch {
        Write-MXTermStatus -Kind failure -Message "MXTerm returned invalid decision data."
        return $null
    }
}

function Invoke-MXTermDispatch {
    param([string]$Line)

    $decision = Invoke-MXTermResolve -Line $Line
    if ($null -eq $decision) {
        return $true
    }

    Show-MXTermDecision -Decision $decision

    if ($decision.route -eq "block") {
        return $true
    }

    if ($decision.requires_confirmation) {
        $answer = Read-Host "Execute this command? [y/N]"
        if ($answer -notmatch '^(y|yes)$') {
            return $true
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($decision.shell_code)) {
        Invoke-Expression $decision.shell_code | Out-Host
    }
    return $true
}

function Invoke-MXTermManual {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$InputText
    )

    $line = ($InputText -join ' ').Trim()
    if ([string]::IsNullOrWhiteSpace($line)) {
        return
    }
    Invoke-MXTermDispatch -Line $line | Out-Null
}

Set-Alias __MXTERM_EXPLICIT_COMMAND__ Invoke-MXTermManual -Scope Global

if ("__MXTERM_AUTO_CAPTURE__" -eq "1") {
    Import-Module PSReadLine -ErrorAction SilentlyContinue
}

if ("__MXTERM_AUTO_CAPTURE__" -eq "1" -and (Get-Module PSReadLine)) {
    Set-PSReadLineKeyHandler -Key Enter -BriefDescription "MXTermAcceptLine" -ScriptBlock {
        $line = $null
        $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
        if ([string]::IsNullOrWhiteSpace($line)) {
            [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
            return
        }
        $firstToken = Get-MXTermFirstToken -Line $line
        if (Test-MXTermShellResolvesToken -Token $firstToken) {
            [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
            return
        }
        if (-not (Test-MXTermShouldAutoCapture -Line $line)) {
            [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
            return
        }
        $escaped = $line.Replace("'", "''")
        $rewritten = "$env:MXTERM_HOOK_EXPLICIT_COMMAND '$escaped'"
        [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert($rewritten)
        [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
    }
    $env:MXTERM_HOOK_ENTER_HANDLER = "1"
}

if ("__MXTERM_SHOW_BANNER__" -eq "1") {
    Write-Host "[MXTerm] loaded for PowerShell. Enter auto-capture: __MXTERM_AUTO_CAPTURE__ / mode=__MXTERM_AUTO_CAPTURE_MODE__. Use __MXTERM_EXPLICIT_COMMAND__ <text> for explicit AI mode." -ForegroundColor Cyan
}
