# Web interface layer

The Streamlit demo lives at the **repository root** as `ui.py` (not inside this package). It is a separate UI client that talks to the FastAPI backend over HTTP (`POST /generate_response`, etc.).

Future dedicated web frontend (React/Vue) would also sit under `app/interfaces/web/` or a sibling frontend repo, calling the same API.
