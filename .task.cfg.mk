USAGE={a.bold}{a.cyan} viv isn't venv{a.end}\n\n\ttasks:\n
PHONIFY=1
HELP_SEP={a.b_blue}>>>{a.end}

-include .task.mk
$(if $(filter help,$(MAKECMDGOALS)),$(if $(wildcard .task.mk),,.task.mk: ; curl -fsSL https://raw.githubusercontent.com/daylinmorgan/task.mk/v23.1.1/task.mk -o .task.mk))
