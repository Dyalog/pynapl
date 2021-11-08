# Google Sheets API interaction

This demo interacts with the Google Sheets API via `gspread`, a Python module.
The purpose of this demo is to showcase how useful it can be to use Python's modules
to leverage an API wrapper.

This demo fetches some dummy data from [this public sheet][demo-sheet]
that can be read by anyone.
The sheet was set up so that there is a service account with enough
permissions to _read_ the contents of that sheet through the API.


## Run this demo

Start of by installing all the Python dependencies with

```bash
python -m pip install -r requirements.txt
```

Now, you want to be able to access the Google Sheets API programmatically.
For that, you need to set up a service account.
Luckily, the [`gspread` docs][gspread-docs-auth] walk you through the set up you need to do.

To test if everything is working fine, you can create a copy of [this spreadsheet][demo-sheet].
Then, you will want to share the copied sheet with the service account email you created
by following the instructions in the `gspread` documentation.

After that is done, you can use the `test_access.py` CLI to test the connection.

Just run the command

```bash
python test_access.py -c "path/to/credentials/file.json" -s "copied_spreadsheet_name"
```

or run

```bash
python test_access.py --help
```

to get help.

Once you _can_ connect to the sheet, it's time to fetch its data from within APL:

```APL
      ]load path/to/pynapl/Py
      ]cd path/to/pynapl
      py ← ⎕NEW Py.Py
      data ← py FetchDemoGSpreadData.aplf 'path/to/credentials/pynapl-gspread-demo-key.json'
      ⍴data
10 2
      ⍉data    ⍝ The numbers of the second column of the data were converted to numbers.
┌─────────┬──────────────┬─────────┬───┬──────────┬─────────┬──────────────┬───┬──────────────┬─────────┐
│Groceries│Transportation│Groceries│Fun│Restaurant│Groceries│Transportation│Fun│Transportation│Groceries│
├─────────┼──────────────┼─────────┼───┼──────────┼─────────┼──────────────┼───┼──────────────┼─────────┤
│15       │1.5           │10.2     │8  │30        │0.99     │1.5           │8  │3             │12.3     │
└─────────┴──────────────┴─────────┴───┴──────────┴─────────┴──────────────┴───┴──────────────┴─────────┘
```


[demo-sheet]: https://docs.google.com/spreadsheets/d/1pM5DbsyquFRHPqkhC0oWEK3KWsC3VH92Im8kns5Pkq4
[gspread-docs-auth]: https://docs.gspread.org/en/latest/oauth2.html
