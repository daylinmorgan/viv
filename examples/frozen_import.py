#!/usr/bin/env python3
"""
This import statement was generated using
`viv freeze pandas tabulate` on 2022.12.19

Using viv freeze ensures future runs of this
script will use the same essential environment
"""

__import__("viv").use(
    "numpy==1.24.0",
    "pandas==1.5.2",
    "python-dateutil==2.8.2",
    "pytz==2022.7",
    "six==1.16.0",
    "tabulate==0.9.0",
)  # noqa

import pandas as pd

df = pd.DataFrame({"x": range(10), "y": range(10)})

print(df.to_markdown())
