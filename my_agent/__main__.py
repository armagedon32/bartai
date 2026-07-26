import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from my_agent.web.server import run
        run()
    else:
        from my_agent.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
