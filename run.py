import sys
import uvicorn
import webbrowser
import threading
import time

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def open_browser():
    time.sleep(1.5)
    url = "http://localhost:8000"
    print("\n=======================================================")
    print(f"[*] S.T.R.I.D.E Urban AI Command Center is Live at: {url}")
    print("=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not auto-open browser: {e}")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")

