"""
Data Agent CLI Entry Point
==========================

Run the data agent:
    python -m da
"""

from da.agent import data_agent

if __name__ == "__main__":
    data_agent.cli_app(stream=True)
