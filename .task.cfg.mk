USAGE={a.bold}{a.cyan} viv tasks{a.end}:\n
PHONIFY=1
HELP_SEP={a.b_blue}>>>{a.end}

-include .task.mk
$(if $(wildcard .task.mk),,.task.mk: ; curl -fsSL https://raw.githubusercontent.com/daylinmorgan/task.mk/v23.1.2/task.mk -o .task.mk)
