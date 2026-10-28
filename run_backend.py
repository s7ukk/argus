import sys
import os
import multiprocessing

# Ensure root SSL certificates work out of the box on macOS
if sys.platform == "darwin":
    try:
        import ssl
        try:
            import certifi
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        except Exception:
            pass
        try:
            ssl.create_default_context().load_default_certs()
        except Exception:
            ssl._create_default_https_context = ssl._create_unverified_context
    except Exception:
        pass

# Ensure script directory and parent are in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

parent_dir = os.path.dirname(script_dir)
if parent_dir and parent_dir not in sys.path:
    sys.path.insert(1, parent_dir)

res_path = os.getenv("ARGUS_RESOURCES_PATH")
if res_path and res_path not in sys.path:
    sys.path.insert(0, res_path)

if sys.platform == "darwin":
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for p in [
        os.path.join(os.path.dirname(os.path.dirname(exe_dir)), "Resources"),
        os.path.join(os.path.dirname(os.path.dirname(exe_dir)), "Resources", "backend"),
        os.path.join(exe_dir, "Resources"),
        os.path.join(exe_dir, "backend"),
    ]:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

# PyInstaller static analyzer anchors
try:
    import multipart
except ImportError:
    pass

try:
    import uvicorn.logging
    import uvicorn.loops
    import uvicorn.loops.asyncio
    import uvicorn.protocols
    import uvicorn.protocols.http
    import uvicorn.protocols.http.h11_impl
    import uvicorn.lifespan
    import uvicorn.lifespan.on
except ImportError:
    pass

# Automatic dependency recovery if running via system Python
if not getattr(sys, "frozen", False):
    try:
        import uvicorn
        import fastapi
        import multipart
    except ImportError:
        try:
            import subprocess
            print("[Argus Backend]: Attempting automatic dependency installation...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "fastapi", "uvicorn[standard]", "pydantic", "python-multipart", "psutil", "pyautogui", "pyperclip"],
                check=False
            )
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
