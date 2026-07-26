#!/usr/bin/env python3
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from my_agent.web.server import run
        run()
    else:
        from my_agent.cli import main
        main()
