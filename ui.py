"""Compatibility shim. The Second Look entrypoint is Second_Look.py (Streamlit takes the
sidebar label from the entrypoint's filename). Prefer:  .venv/bin/streamlit run Second_Look.py
This file only forwards, so the older `streamlit run ui.py` command keeps working."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("Second_Look.py")), run_name="__main__")
