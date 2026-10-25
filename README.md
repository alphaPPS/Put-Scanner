# Put Scanner

A free tool for people who sell cash-secured puts. Give it a list of tickers, a target delta (for example 0.10) and an expiry date, and it finds the put on each ticker whose delta is closest to your target, using your own Robinhood account for live option data.

For each ticker it shows the stock price, strike, mark, bid/ask, delta, implied volatility, open interest, volume, weekly and annualized return (mark ÷ strike), analyst buy %, and dividend yield, and saves the results to a CSV file. It is read-only and never places orders.

There are two ways to run it, both on your own computer:

- **Browser version** (`put_scanner_web.py`): a page in your browser with a login form, sortable results and a CSV download.
- **Terminal version** (`put_scanner.py`): prints the table in the terminal.

![Scan results in the browser version](docs/screenshots/results.png)

<sub>Screenshots use made-up sample data.</sub>

## Download and install

You need a Robinhood account and Python 3.9 or newer. Setup takes about five minutes and you only do it once.

### 1. Install Python

- **Mac:** download the installer from [python.org/downloads](https://www.python.org/downloads/) and run it.
- **Windows:** download the installer from [python.org/downloads](https://www.python.org/downloads/). On the first screen, tick **Add python.exe to PATH**, then click **Install Now**.
- **Linux:** Python is usually already installed. If not, on Ubuntu or Debian run `sudo apt install python3 python3-venv`.

To check it worked, open a terminal (Mac: **Terminal** app; Windows: **Command Prompt**; Linux: your terminal) and run `python3 --version` (Windows: `py --version`).

### 2. Get the code

Either way works:

- **Download ZIP (easiest):** on this page, click the green **Code** button, then **Download ZIP**. Unzip it somewhere you'll find it, such as your Documents folder.
- **Or with git:** `git clone https://github.com/alphaPPS/Put-Scanner.git`

### 3. Set it up

In your terminal, go into the folder you just unzipped or cloned, then run the commands for your system. The folder name may be `Put-Scanner-main` if you used the ZIP.

**Mac and Linux:**

```bash
cd ~/Documents/Put-Scanner-main
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (Command Prompt):**

```bat
cd %USERPROFILE%\Documents\Put-Scanner-main
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

This creates a private Python environment in a `venv` folder and installs the two libraries the scanner needs.

### 4. Run it

Each time you want to use it, open a terminal in the folder, turn on the environment, and start the browser version:

| | Turn on the environment | Start the scanner |
|---|---|---|
| Mac / Linux | `source venv/bin/activate` | `python3 put_scanner_web.py` |
| Windows | `venv\Scripts\activate` | `python put_scanner_web.py` |

Your browser opens the scanner page. Log in with your Robinhood email and password, and you're ready to scan (see [Browser version](#browser-version-runs-on-your-computer) below). Press Ctrl+C in the terminal when you're done.

### Updating to a new version

Download the ZIP again (your `venv` folder can be copied over or recreated with step 3), or if you used git, run `git pull` in the folder.

## Terminal version

Edit `tickers.list` (one ticker per line) and run:

```bash
python3 put_scanner.py -f tickers.list -d 0.10 -t 15May2026
python3 put_scanner.py -f tickers.list -d 0.10 -t 5/15/2026
python3 put_scanner.py -f tickers.list -d 0.10 -t 2026-05-15
python3 put_scanner.py -f tickers.list -d 0.10          # defaults to next Friday
```

- `-f` text file with one ticker per line (required)
- `-d` target delta as a positive number (default 0.10)
- `-t` expiry date

On Windows, use `python` instead of `python3`.

You are asked for your Robinhood email and password at login. The session is saved to `~/.tokens/robinhood.pickle`, which is never committed.

## Browser version (runs on your computer)

The same scan with a page in your browser instead of the terminal. It runs only on your own computer (served from `127.0.0.1`), and your Robinhood login goes straight from it to Robinhood.

```bash
source venv/bin/activate
python3 put_scanner_web.py
```

Your browser opens `http://127.0.0.1:8765`. Log in, paste tickers (or load a `.list` file), pick a delta and an expiry date, and click **Run scan**. If Robinhood asks for a texted or emailed code, a box for it appears on the page; if it asks you to approve in the app, approve it there. Results can be sorted by clicking a column, and **Download CSV** saves the same CSV the terminal version writes. If a saved session exists it is used automatically, and **Log out** deletes it.

<p>
  <img src="docs/screenshots/login.png" alt="Login and scan settings" width="49%">
  <img src="docs/screenshots/results-dark.png" alt="Results in dark mode" width="49%">
</p>

Options: `--port 9000` to use another port, `--no-browser` to not open the browser. Press Ctrl+C in the terminal to stop.

## Troubleshooting

If login fails, delete the saved session and run again:

```bash
rm ~/.tokens/robinhood.pickle                 # Mac / Linux
del %USERPROFILE%\.tokens\robinhood.pickle     # Windows
```

If `python3` or `py` isn't found, Python isn't installed or (on Windows) wasn't added to PATH: run the installer again and tick **Add python.exe to PATH**.

If `pip install` fails, make sure you turned on the environment first: your terminal prompt should start with `(venv)`.

## Disclaimer

This tool is for information only and is not financial advice. It uses the unofficial `robin_stocks` library, which Robinhood does not support and which can stop working when Robinhood changes things. Data may be delayed or wrong, so check anything important in Robinhood before you trade. It comes with no warranty, and you use it at your own risk.

## License

[MIT](LICENSE). Free for anyone to use, copy, and change.
