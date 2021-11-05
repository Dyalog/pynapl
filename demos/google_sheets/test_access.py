"""
Test the `gspread` access to the demo sheet.
"""


import pathlib

import gspread

KEY_FILE = pathlib.Path(__file__).parent / "pynapl-gspread-demo-key.json"
DEMO_SHEET = "pynapl_demo"

gc = gspread.service_account(filename=KEY_FILE)
sh = gc.open(DEMO_SHEET)

assert sh is not None
