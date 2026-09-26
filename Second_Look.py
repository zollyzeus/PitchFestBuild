"""Compatibility shim: the product is now Relook.py (this file kept only so
`streamlit run Second_Look.py` -- as referenced by docs/02-baton-plan.md -- still works).
Prefer:  .venv/bin/streamlit run Relook.py
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("Relook.py")), run_name="__main__")
