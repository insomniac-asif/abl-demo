"""Entry point: `python demo.py`.

The walkthrough lives in the package (abl_demo.cli) so the installed console
script `abl-demo` and this file run exactly the same thing.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from abl_demo.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
