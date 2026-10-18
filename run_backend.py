import sys
import multiprocessing
import uvicorn
import backend.server as server

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    uvicorn.run(server.app, host="127.0.0.1", port=18274, log_level="warning")
