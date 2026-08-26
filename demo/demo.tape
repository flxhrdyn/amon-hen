Output demo/demo.gif

Set Shell "powershell"
Set FontSize 15
Set Width 920
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 40ms
Set Padding 20

Type "Remove-Item -ErrorAction SilentlyContinue demo/index.db; Clear-Host"
Enter
Sleep 600ms

Type "uv run amon-hen index demo/cctv-people-demo.webm --sampler adaptive --db demo/index.db"
Enter
Sleep 5s

Type `uv run amon-hen search "a person holding an umbrella" --db demo/index.db`
Enter
Sleep 4s

Type `uv run amon-hen search "a car passing by" --db demo/index.db`
Enter
Sleep 5s
