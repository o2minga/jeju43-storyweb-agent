# Windows SAPI(System.Speech) 오프라인 TTS — agent/generate/audio_backend.py가 subprocess로
# 호출한다. 클라우드 API 키가 필요 없는 대신 Windows(및 해당 언어팩의 음성)에서만 동작한다.
#
# 사용법:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tts-sapi.ps1 `
#     -TextPath <입력 텍스트 파일(UTF-8)> -OutPath <출력 wav 경로> -VoiceName "Microsoft Heami Desktop"
param(
    [Parameter(Mandatory = $true)][string]$TextPath,
    [Parameter(Mandatory = $true)][string]$OutPath,
    [string]$VoiceName = "Microsoft Heami Desktop"
)

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

try {
    $synth.SelectVoice($VoiceName)
} catch {
    Write-Error "지정한 음성을 찾을 수 없습니다: $VoiceName (설치된 음성 목록은 GetInstalledVoices()로 확인)"
    exit 1
}

$text = Get-Content -LiteralPath $TextPath -Raw -Encoding UTF8
$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$synth.SetOutputToWaveFile($OutPath)
$synth.Speak($text)
$synth.Dispose()
