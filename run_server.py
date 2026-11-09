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
    is_cloud = "RENDER" in os.environ or "RENDER_SERVICE_ID" in os.environ
    default_host = "127.0.0.1" if sys.platform == "win32" and not is_cloud else "0.0.0.0"
    host = os.environ.get("HOST", default_host)
    port = int(os.environ.get("PORT", 8000))
    display_host = "127.0.0.1" if host == "0.0.0.0" else host

    print("=" * 65, flush=True)
    print("[*] Privacy-Aware AI Model Unlearning Evaluation Demonstrator", flush=True)
    print("=" * 65, flush=True)
    print(f"  * Interactive UI:   http://{display_host}:{port}", flush=True)
    print(f"  * Backend API:      http://{display_host}:{port}/api", flush=True)
    print(f"  * API Swagger Docs: http://{display_host}:{port}/docs", flush=True)
    if host == "0.0.0.0":
        print(f"  * Network Bind:     0.0.0.0:{port} (listening on all interfaces)", flush=True)
    print("=" * 65, flush=True)
    
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)
