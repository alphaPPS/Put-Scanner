# Put Scanner

Scans a list of tickers on Robinhood for the put option, expiring on a given date, whose delta is closest to a target. It prints a table with weekly and annualized return, buy %, and dividend yield, and saves the results to a CSV file. The script is read-only and places no orders.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install robin_stocks tabulate
```

## Usage

```bash
python3 put_scanner.py -f tickers.list -d 0.10 -t 15May2026
python3 put_scanner.py -f tickers.list -d 0.10 -t 5/15/2026
python3 put_scanner.py -f tickers.list -d 0.10 -t 2026-05-15
python3 put_scanner.py -f tickers.list -d 0.10          # defaults to next Friday
```

- `-f` text file with one ticker per line (required)
- `-d` target delta as a positive number (default 0.10)
- `-t` expiry date

You are asked for your Robinhood email and password at login. The session is saved to `~/.tokens/robinhood.pickle`, which is never committed.

## Troubleshooting

If login fails, delete the saved session and run again:

```bash
rm ~/.tokens/robinhood.pickle
```
