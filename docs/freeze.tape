Set Height 750
Set Width 1500
Set Theme "Catppuccin Mocha"
Output ./docs/freeze.gif

Type "viv list"
Enter
Sleep 2s
Type "viv freeze requests bs4"
Enter
Sleep 5s
Type "viv list"
Enter
Sleep 3s
Type "viv freeze requests bs4 --keep --path relative"
Enter
Sleep 5s
Type "viv list"
Enter
Sleep 5s
