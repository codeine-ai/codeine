"""
Lightweight server entry point.

Sets RETER_PROJECT_ROOT from --project arg BEFORE heavy imports,
matching the behavior of `python -m reter_code.server`.
"""

import os
import sys


def _early_setup():
    """Parse --project early to set RETER_PROJECT_ROOT before imports."""
    project_path = None
    for i, arg in enumerate(sys.argv):
        if arg in ('--project', '-p') and i + 1 < len(sys.argv):
            project_path = os.path.abspath(sys.argv[i + 1])
            break
        elif arg.startswith('--project='):
            project_path = os.path.abspath(arg.split('=', 1)[1])
            break
    if not project_path:
        project_path = os.getcwd()
    os.environ['RETER_PROJECT_ROOT'] = project_path


def main():
    """Server entry point with early env setup."""
    _early_setup()
    from .server.reter_server import main as server_main
    server_main()
