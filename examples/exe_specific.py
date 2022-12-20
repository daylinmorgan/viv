#!/usr/bin/env python3
"""
This script will generate a vivenv that is executable specific.
This means if it is run using a different python version or executable
it will generate a new vivenv.

It may be important to require a exe specificty if you are frequently running
different version of pythons and rely on c extension modules as in numpy.
"""

__import__("viv").activate("numpy", "termplotlib", track_exe=True)

import numpy as np
import termplotlib as tpl

x = np.linspace(0, 2 * np.pi, 10)
y = np.sin(x)

fig = tpl.figure()
fig.plot(x, y, label="data", width=50, height=15)
fig.show()
