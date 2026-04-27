# Rubbish theory — Dynaconf diagnostic

Throwaway file for debugging the `AttributeError: 'Settings' object has no
attribute 'LLM'` we hit on Windows on 2026-04-27.

## Run this from `src/`

```powershell
python -c "import os; from core.config import settings; print('APP_ENV=', os.environ.get('APP_ENV')); print('current_env=', settings.current_env); print('top-level keys=', sorted(settings.keys())); print('config file exists=', __import__('pathlib').Path('./conf/config.yaml').exists()); print('config file abs=', __import__('pathlib').Path('./conf/config.yaml').resolve())"
```

## What each line tells us

| Line | If empty / unexpected | What it means |
|---|---|---|
| `APP_ENV=` | empty / `None` | Env var unset → Dynaconf falls back to its default. Should still work because YAML has a `local:` profile and Dynaconf treats unset switcher as `local` for `environments=True`. |
| `current_env=` | not `local` or `dev` | Wrong profile selected. Set `$env:APP_ENV = "local"` and re-run. |
| `top-level keys=` | empty list | YAML didn't load at all. Path-resolution issue. Check next line. |
| `config file exists=` | `False` | CWD isn't where Dynaconf expects. We're using `./conf/config.yaml` (CWD-relative) — must run from `src/`. |
| `config file abs=` | not the right absolute path | Confirms what the relative path resolves to. |

## Likely culprits, in order

1. **Path resolution**: weave's `core/config.py` uses `settings_files=["./conf/config.yaml"]` — CWD-relative. If anything changes CWD before Dynaconf reads the file, it loads nothing. Fix: change to `__file__`-relative (the `_CONFIG_FILE = Path(__file__).resolve().parent.parent / "conf" / "config.yaml"` pattern).
2. **`load_dotenv=True`** picks up a `.env` in CWD that overrides `APP_*` keys.
3. **Stale `__pycache__`** for `config.py` — `find . -name __pycache__ -type d -exec rm -rf {} +` and retry.

Delete this file once the bug is resolved.
