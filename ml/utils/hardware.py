import platform
import psutil
import torch


def get_hardware_info() -> dict:
    """Retrieve system hardware and accelerator information."""
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "processor": platform.processor() or "x86_64",
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        info["cuda_device_name"] = torch.cuda.get_device_name(0)
        info["cuda_device_count"] = torch.cuda.device_count()
        info["cuda_capability"] = torch.cuda.get_device_capability(0)
    else:
        info["device"] = "cpu"
    return info


def get_device() -> torch.device:
    """Return torch.device (cuda if available else cpu)."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
