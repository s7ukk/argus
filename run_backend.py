import sys
import os
import multiprocessing

# Ensure script directory and parent are in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

parent_dir = os.path.dirname(script_dir)
if parent_dir and parent_dir not in sys.path:
    sys.path.insert(1, parent_dir)

# Automatic dependency recovery if running via system Python
try:
    import uvicorn
    import fastapi
except ImportError:
    try:
        import subprocess
        print("[Argus Backend]: Attempting automatic dependency installation...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "fastapi", "uvicorn", "pydantic"], check=False)
        import uvicorn
        import fastapi
    except Exception as e:
        print(f"[Argus Backend]: Dependency recovery error: {e}", file=sys.stderr)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    try:
        import backend.server as server
        print("[Argus Backend]: Starting FastAPI server on 127.0.0.1:18274...")
        uvicorn.run(
            server.app,
            host="127.0.0.1",
            port=18274,
            log_level="warning",
            loop="asyncio",
            http="h11"
        )
    except Exception as e:
        print(f"[Argus Backend Fatal Error]: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
