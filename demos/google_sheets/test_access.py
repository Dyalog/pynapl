"""
Test the `gspread` access to the demo sheet.
"""


import argparse
import pathlib

import gspread

KEY_FILE = pathlib.Path(__file__).parent / "pynapl-gspread-demo-key.json"
DEMO_SHEET = "pynapl_demo"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--credentials",
        metavar="CREDENTIALS_PATH",
        help="Path to service account credentials JSON.",
        default=KEY_FILE,
    )
    parser.add_argument(
        "-s",
        "--sheet",
        help="Name of the spreadsheet to try to access.",
        default=DEMO_SHEET,
    )

    args = parser.parse_args()

    gc = gspread.service_account(filename=args.credentials)
    sh = gc.open(args.sheet)

    assert sh is not None, "Failed to connect to correct sheet!"

    print("Successfully connected.")
