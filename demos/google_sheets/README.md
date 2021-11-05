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

To make sure that everything is set up so that you can use `gspread` to connect
to the sheet, run the command

```bash
python test_access.py
```

No news is good news, and it means you can connect to the sheet.

If you _can_ connect to the sheet, then it's time to fetch its data from within APL:

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
