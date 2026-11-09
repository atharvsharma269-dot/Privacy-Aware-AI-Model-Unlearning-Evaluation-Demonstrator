with open("backend/app/services/tofu_service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

landmarks = [
    "class TOFUUnlearningService:",
    "def load_dataset(",
    "def load_global_registry(",
    "def subscribe_author_status(",
    "def get_author_status(",
    "def set_author_status(",
    "def get_author_diff(",
    "def reset_dataset(",
    "def list_authors(",
    "def get_author_details(",
    "def query_qa(",
    "def forget_author(",
    "def forget_qa(",
    "def forget_attribute(",
    "def forget_group(",
    "def verify_retention(",
    "def compute_forget_impact(",
    "def create_chat_session(",
    "def list_chat_sessions(",
    "def post_chat_message(",
]

found = {}
for i, line in enumerate(lines):
    for lm in landmarks:
        if lm in line and lm not in found:
            found[lm] = i

for lm in landmarks:
    print(f"{lm} -> line {found.get(lm, 'NOT FOUND')}")
