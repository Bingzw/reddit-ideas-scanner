param(
  [string]$ProjectDir = "D:\bingz_github\reddit_ideas",
  [string]$PythonExe = "D:\bingz_github\reddit_ideas\.venv\Scripts\python.exe"
)

Set-Location $ProjectDir
& $PythonExe -m reddit_ideas.cli run-once --period daily
