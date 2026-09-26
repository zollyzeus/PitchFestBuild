"""Compatibility shim. The Relook entrypoint is Relook.py (Streamlit takes the
sidebar label from the entrypoint's filename). Prefer:  .venv/bin/streamlit run Relook.py
This file only forwards, so the older `streamlit run ui.py` command keeps working."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("Relook.py")), run_name="__main__")
