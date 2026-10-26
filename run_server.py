import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("[*] Privacy-Aware AI Model Unlearning Evaluation Demonstrator")
    print("=" * 65)
    print("  * Interactive UI:   http://127.0.0.1:8000")
    print("  * Backend API:      http://127.0.0.1:8000/api")
    print("  * API Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 65)
    
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
