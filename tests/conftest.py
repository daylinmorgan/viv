import os
import shutil
from pathlib import Path

cache = (Path(__file__).parent / ".viv-cache").absolute()
if cache.is_dir():
    shutil.rmtree(cache)

# remove local settings
os.environ = {k: v for k, v in os.environ.items() if not k.startswith("VIV_")}

os.environ["VIV_CACHE"] = str(cache)
