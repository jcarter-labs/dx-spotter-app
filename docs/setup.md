# Setup (macOS)

Requires Python 3.13+ from Homebrew or python.org (never `/usr/bin/python3`, whose Tk is too old) with Tk 8.6 or 9.x.
Checked on 2026-09-30: Homebrew Python 3.13.15, Tk 9.0, pip 26.2.

```sh
brew install python@3.13 python-tk@3.13   # only if Python or Tk is missing
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt            # requests, Pillow, pytest
pytest
```

Git publishing: `git config user.name` / `user.email` set, `ssh -T git@github.com` succeeds, remote `origin` is `git@github.com:jcarter-labs/RSGB-3.git`.
