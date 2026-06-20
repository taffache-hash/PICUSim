#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.methods_appendix import save_methods_appendix

if __name__ == "__main__":
    print(json.dumps(save_methods_appendix(), indent=2))
