#!/usr/bin/env python3
"""Root-level executable entry point (thin wrapper around fly_in.main).

Lets the project be run as `./main.py <map>` in addition to
`python3 -m fly_in.main <map>`.
"""

from fly_in.main import main

if __name__ == "__main__":
    main()
