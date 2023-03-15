#!/usr/bin/env python3

__import__("viv").use("pyfiglet==0.8.post1")  # noqa

from pyfiglet import Figlet

if __name__ == "__main__":
    f = Figlet(font="slant")
    figtxt = f.renderText("viv").splitlines()
    figtxt[-2] += " isn't venv!"
    print("\n".join(figtxt))
