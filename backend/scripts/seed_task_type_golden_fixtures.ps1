# Generates backend/app/fixtures/task_type_golden/*.json (no Python required)
$ErrorActionPreference = "Stop"
$OutDir = Join-Path $PSScriptRoot "..\app\fixtures\task_type_golden"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-LongText([string]$Topic, [int]$Words = 130) {
    $parts = @(
        "Dieser Block erklaert $Topic Schritt fuer Schritt mit Beispielen aus dem Schulheft.",
        "Wir wiederholen Begriffe, zeigen einen Rechenweg und verbinden die Aufgabe mit bekanntem Stoff."
    )
    $i = 1
    while (($parts -join " ").Split(" ").Count -lt $Words) {
        $parts += "inhalt$i"
        $i++
    }
    return ($parts -join " ")
}

function Get-Questions([string]$Prefix, [int]$Count, [bool]$WithExplanation = $true) {
    $items = @()
    for ($i = 0; $i -lt $Count; $i++) {
        $q = [ordered]@{
            q = "$Prefix Frage $($i + 1)?"
            options = @("Antwort A$i", "Antwort B$i", "Antwort C$i", "Antwort D$i")
            answer = 0
        }
        if ($WithExplanation) {
            $q.explanation = "Variante 1: 12 + 8 = 20. Variante 2: 10 + 8 = 18, dann +2 = 20."
        }
        $items += [pscustomobject]$q
    }
    return $items
}

function Get-StandardModules([string]$Task, [int]$ModuleCount = 5, [int]$QCount = 4, [bool]$WithExplanation = $true) {
    $mods = @()
    for ($i = 0; $i -lt $ModuleCount; $i++) {
        $mods += [pscustomobject]@{
            title = "Block $($i + 1)"
            content = @{ text = (Get-LongText "$Task Thema $($i + 1)") }
            quiz = @{ questions = (Get-Questions "Block $($i + 1)" $QCount $WithExplanation) }
        }
    }
    return $mods
}

$builders = @{
    mixed = { Get-StandardModules "mixed" }
    explain = { Get-StandardModules "explain" 5 2 }
    quiz = { Get-StandardModules "quiz" }
    practice = { Get-StandardModules "practice" }
    math = {
        $mods = @()
        for ($i = 0; $i -lt 5; $i++) {
            $mods += [pscustomobject]@{
                title = "Rechnen $($i + 1)"
                content = @{
                    text = (Get-LongText "Dezimalrechnung")
                    practice = @(@{
                        prompt = "Berechne 3,2 + 4,8"
                        answer = "8"
                        hint = "Komma unter Komma"
                        answer_type = "number"
                    })
                }
                quiz = @{
                    questions = @(
                        [pscustomobject]@{
                            q = "Was ist 7,2 : 9 in Bereich $($i + 1)?"
                            options = @("0,8", "0,08", "8", "0,72")
                            answer = 0
                            explanation = "Variante 1: 72 / 9 = 8, Komma eine Stelle = 0,8. Variante 2: 72 / 9 = 8, das sind 8 Zehntel = 0,8."
                        }
                    ) + (Get-Questions "Mathe $($i + 1)" 3)
                }
            }
        }
        return $mods
    }
    workbook = { Get-StandardModules "workbook" }
    review = { Get-StandardModules "review" }
    exam = { Get-StandardModules "exam" 5 4 $false }
    vocab = {
        $mods = @()
        for ($i = 0; $i -lt 5; $i++) {
            $mods += [pscustomobject]@{
                title = "Vokabeln Set $($i + 1)"
                content = @{
                    text = "Wort: apple - Bedeutung: Apfel - Beispiel: I eat an apple every day. Wort: house - Bedeutung: Haus - Beispiel: This is my house. " + (Get-LongText "Englisch Vokabeln" 110)
                    practice = @(@{
                        prompt = "Uebersetze: book"
                        answer = "Buch"
                        hint = "Schulbuch"
                        answer_type = "text"
                    })
                }
                quiz = @{ questions = (Get-Questions "Vokabel" 4 $false) }
            }
        }
        return $mods
    }
    interactive = {
        $mods = @()
        for ($area = 0; $area -lt 4; $area++) {
            $cards = @()
            $questions = @()
            for ($j = 0; $j -lt 8; $j++) {
                $cards += @{ question = "Lernkarte $($area + 1)-$($j + 1)?"; answer = "Antwort $($area + 1)-$($j + 1)." }
                if ($j -eq 0) {
                    $questions += [pscustomobject]@{
                        q = "Quiz $($area + 1)-$($j + 1): Was ist 6 mal 7?"
                        options = @("42", "36", "48", "40")
                        answer = 0
                        explanation = "Variante 1: 6 mal 7 = 42. Variante 2: 6 mal 5 = 30, 6 mal 2 = 12, 30 + 12 = 42."
                    }
                } else {
                    $questions += @{ q = "Quiz $($area + 1)-$($j + 1)?"; options = @("A", "B", "C", "D"); answer = 0 }
                }
            }
            $mods += [pscustomobject]@{
                title = "Bereich $($area + 1)"
                content = @{
                    cards = $cards
                    knowledge = @(@{ title = "Merke"; text = "Wichtiger Fakt aus dem Heft." })
                }
                quiz = @{ questions = $questions }
            }
        }
        return $mods
    }
}

$hints = @{
    mixed = "Bruchrechnen Klasse 5"
    explain = "Photosynthese Einstieg"
    quiz = "Erdkunde Europa"
    practice = "Satzglieder ueben"
    math = "Dezimalrechnung"
    workbook = "Arbeitsblatt Addition"
    review = "Wiederholung Multiplikation"
    exam = "Kurzpruefung Grammatik"
    vocab = "Englisch Tiere"
    interactive = "Trainer Dezimalzahlen"
}

foreach ($task in $builders.Keys) {
    $meta = [ordered]@{
        task_type = $task
        subject_hint = $hints[$task]
    }
    if ($task -eq "interactive") {
        $meta.min_cards = 30
        $meta.min_questions = 30
    }
    $payload = [ordered]@{
        _meta = $meta
        modules = & $builders[$task]
    }
    $path = Join-Path $OutDir "$task.json"
    $json = $payload | ConvertTo-Json -Depth 20
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $json + "`n", $utf8NoBom)
    Write-Host "wrote $task.json"
}
