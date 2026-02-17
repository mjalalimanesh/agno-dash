"""CLI entry point: python -m dash"""

from dash.agent import dash

if __name__ == "__main__":
    dash.cli_app(stream=True)
