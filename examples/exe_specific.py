#!/usr/bin/env python3
"""
This script will generate a vivenv that is executable specific.
This means if it is run using a different python version or executable
it will generate a new vivenv.

It may be important to require a exe specificty if you are frequently running
different version of pythons and rely on c extension modules as in numpy.
"""
__import__("viv").use("numpy", "plotext", track_exe=True)  # noqa

import numpy as np
import plotext as plt

x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x)

plt.scatter(x, y)
plt.title("Scatter Plot")  # to apply a title
plt.plot_size(plt.tw() / 4, plt.th() / 4)
plt.theme("pro")
plt.show()  # to finally plot
