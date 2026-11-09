import re

with open("backend/app/services/tofu_service.py", "r", encoding="utf-8") as f:
    code = f.read()

print("Original length:", len(code))
