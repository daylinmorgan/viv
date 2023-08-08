#!/usr/bin/env -S viv run -s
# In order to run, this script needs the following 3rd party libraries
#
# Script Dependencies:
#    requests
#    rich     # Needed for the output
#
#    # Not needed - just to show that fragments in URLs do not
#    # get treated as comments
#    pip @ https://github.com/pypa/pip/archive/1.3.1.zip#sha1=2e15a2d4e7e9f394a9c7a6c905c6a239402a6442

import requests
from rich.pretty import pprint

resp = requests.get("https://peps.python.org/api/peps.json")
data = resp.json()
pprint([(k, v["title"]) for k, v in data.items()][:10])
