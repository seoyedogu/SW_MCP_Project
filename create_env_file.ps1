# .env 파일 생성 스크립트
# PowerShell에서 실행: .\create_env_file.ps1

$envContent = @"
OPENAI_API_KEY=your-api-key-here
"@

$envPath = Join-Path $PSScriptRoot ".env"

# .env 파일 생성
$envContent | Out-File -FilePath $envPath -Encoding UTF8 -NoNewline

Write-Host ".env 파일이 생성되었습니다: $envPath"
Write-Host "파일 내용 확인:"
Get-Content $envPath


