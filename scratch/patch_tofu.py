import re
import ast

with open("backend/app/services/tofu_service.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update __init__ and add properties & helper methods
target_init = """        self.immutable_authors: Dict[str, Dict[str, Any]] = {}
        self.working_authors: Dict[str, Dict[str, Any]] = {}
        self.qa_pairs: List[Dict[str, Any]] = []
        self.audit_timeline: List[Dict[str, Any]] = []
        self.unlearned_authors: set = set()
        self.unlearned_qa: Dict[str, set] = {}  # author_id -> set of forgotten qa_ids
        self.pristine_manifest: Dict[str, Any] = {}
        self._status_listeners: Dict[str, List[Any]] = {}

        self.load_dataset()
        self.load_global_registry()"""

replacement_init = """        self.immutable_authors: Dict[str, Dict[str, Any]] = {}
        self.working_authors: Dict[str, Dict[str, Any]] = {}
        self.qa_pairs: List[Dict[str, Any]] = []
        self.audit_timeline: List[Dict[str, Any]] = []
        self._exp_unlearned_authors: Dict[str, set] = {}
        self._exp_unlearned_qa: Dict[str, Dict[str, set]] = {}
        self.pristine_manifest: Dict[str, Any] = {}
        self._status_listeners: Dict[str, List[Any]] = {}

        self.load_dataset()
        self.load_global_registry()

    @property
    def unlearned_authors(self) -> set:
        return self.get_unlearned_authors(self.resolve_experiment_id())

    @unlearned_authors.setter
    def unlearned_authors(self, val: set) -> None:
        exp_id = self.resolve_experiment_id()
        self._exp_unlearned_authors[exp_id] = set(val)

    @property
    def unlearned_qa(self) -> Dict[str, set]:
        exp_id = self.resolve_experiment_id()
        if exp_id not in self._exp_unlearned_qa:
            self._load_experiment_state(exp_id)
        return self._exp_unlearned_qa.setdefault(exp_id, {a_id: set() for a_id in self.immutable_authors.keys()})

    @unlearned_qa.setter
    def unlearned_qa(self, val: Dict[str, set]) -> None:
        exp_id = self.resolve_experiment_id()
        self._exp_unlearned_qa[exp_id] = val

    def _normalize_author_id(self, author_id: Optional[str]) -> Optional[str]:
        if not author_id:
            return None
        aid = author_id.strip()
        m = re.match(r"^[pP][-_]?(\d{1,4})$", aid)
        if m:
            num = int(m.group(1)) % 200
            return f"TOFU-{num:03d}"
        m_t = re.match(r"^[tT][oO][fF][uU][-_]?(\d{1,4})$", aid)
        if m_t:
            num = int(m_t.group(1)) % 200
            return f"TOFU-{num:03d}"
        return aid

    def resolve_experiment_id(self, experiment_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
        if experiment_id and experiment_id.strip():
            return experiment_id.strip()

        if session_id:
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT experiment_id FROM chat_sessions WHERE id = ?", (session_id,))
                row = c.fetchone()
                conn.close()
                if row and row["experiment_id"]:
                    return row["experiment_id"]
            except Exception:
                pass

        return "default_experiment"

    def _load_experiment_state(self, exp_id: str) -> None:
        self._exp_unlearned_authors[exp_id] = set()
        self._exp_unlearned_qa[exp_id] = {}
        if exp_id == "exp_baseline_pristine":
            return

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                SELECT target_type, target_author_id, qa_ids 
                FROM global_unlearning_registry 
                WHERE experiment_id = ? AND status = 'CONFIRMED'
            \"\"\", (exp_id,))
            rows = c.fetchall()
            for row in rows:
                target_type = row["target_type"]
                author_id = row["target_author_id"]
                try:
                    qa_ids = json.loads(row["qa_ids"]) if row["qa_ids"] else []
                except Exception:
                    qa_ids = []

                if target_type in ("AUTHOR", "GROUP"):
                    self._exp_unlearned_authors[exp_id].add(author_id)
                    if author_id in self.working_authors:
                        for qa in self.working_authors[author_id].get("qa_pairs", []):
                            self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(qa["qa_id"])
                    for q in qa_ids:
                        self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(q)
                elif target_type in ("QA", "ATTRIBUTE"):
                    for q in qa_ids:
                        self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(q)
                    if author_id in self.working_authors:
                        total = len(self.working_authors[author_id].get("qa_pairs", []))
                        if total > 0 and len(self._exp_unlearned_qa[exp_id].get(author_id, set())) >= total:
                            self._exp_unlearned_authors[exp_id].add(author_id)
        except Exception as e:
            logger.error(f"[EXPERIMENT_STATE] Error loading state for {exp_id}: {e}")
        finally:
            conn.close()

    def get_unlearned_authors(self, experiment_id: Optional[str] = None) -> set:
        exp_id = self.resolve_experiment_id(experiment_id)
        if exp_id not in self._exp_unlearned_authors:
            self._load_experiment_state(exp_id)
        return set(self._exp_unlearned_authors.get(exp_id, set()))

    def get_unlearned_qa(self, author_id: str, experiment_id: Optional[str] = None) -> set:
        exp_id = self.resolve_experiment_id(experiment_id)
        norm_aid = self._normalize_author_id(author_id)
        if exp_id not in self._exp_unlearned_qa:
            self._load_experiment_state(exp_id)
        return set(self._exp_unlearned_qa.get(exp_id, {}).get(norm_aid, set()))"""

assert target_init in code, "Target init not found"
code = code.replace(target_init, replacement_init, 1)

# 2. Replace load_global_registry, record_global_unlearning, get_global_registry, _sanitize_existing_chat_sessions
target_registry_block = """    def load_global_registry(self) -> None:
        \"\"\"
        Synchronizes in-memory unlearning state with persistent global_unlearning_registry in SQLite.
        Survives application restarts and ensures all chat sessions access authoritative unlearning records.
        \"\"\"
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
            CREATE TABLE IF NOT EXISTS global_unlearning_registry (
                id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL,
                target_author_id TEXT NOT NULL,
                target_author_name TEXT,
                target_identifier TEXT,
                qa_ids TEXT NOT NULL,
                request_id TEXT,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            \"\"\" )
            c.execute("CREATE INDEX IF NOT EXISTS idx_unlearning_registry_author ON global_unlearning_registry(target_author_id)")

            # Backwards compatibility: sync any confirmed records from forgetting_requests
            try:
                c.execute("SELECT * FROM forgetting_requests WHERE status = 'COMPLETED' AND confirmation_status = 'CONFIRMED'")
                for f_row in c.fetchall():
                    t_id = f_row["target_id"]
                    c.execute("SELECT id FROM global_unlearning_registry WHERE target_author_id = ?", (t_id,))
                    if not c.fetchone() and t_id in self.working_authors:
                        q_ids = [q["qa_id"] for q in self.working_authors[t_id].get("qa_pairs", [])]
                        reg_id = f"REG-MIG-{uuid.uuid4().hex[:6].upper()}"
                        now = datetime.now(timezone.utc).isoformat()
                        c.execute(\"\"\"
                            INSERT INTO global_unlearning_registry (
                                id, target_type, target_author_id, target_author_name,
                                target_identifier, qa_ids, request_id, status, created_at, updated_at
                            ) VALUES (?, 'AUTHOR', ?, ?, 'ALL', ?, ?, 'CONFIRMED', ?, ?)
                        \"\"\", (reg_id, t_id, self.working_authors[t_id]["author_name"], json.dumps(q_ids), f_row["id"], now, now))
                conn.commit()
            except Exception:
                pass

            c.execute("SELECT * FROM global_unlearning_registry WHERE status = 'CONFIRMED'")
            rows = c.fetchall()

            for row in rows:
                target_type = row["target_type"]
                author_id = row["target_author_id"]
                try:
                    qa_ids = json.loads(row["qa_ids"]) if row["qa_ids"] else []
                except Exception:
                    qa_ids = []

                if target_type in ("AUTHOR", "GROUP"):
                    self.unlearned_authors.add(author_id)
                    if author_id in self.working_authors:
                        for qa in self.working_authors[author_id].get("qa_pairs", []):
                            self.unlearned_qa.setdefault(author_id, set()).add(qa["qa_id"])
                    for q in qa_ids:
                        self.unlearned_qa.setdefault(author_id, set()).add(q)
                elif target_type in ("QA", "ATTRIBUTE"):
                    for q in qa_ids:
                        self.unlearned_qa.setdefault(author_id, set()).add(q)
                    if author_id in self.working_authors:
                        total = len(self.working_authors[author_id].get("qa_pairs", []))
                        if total > 0 and len(self.unlearned_qa.get(author_id, set())) >= total:
                            self.unlearned_authors.add(author_id)
            logger.info(f"[GLOBAL_UNLEARNING] Synced {len(rows)} entries from registry ({len(self.unlearned_authors)} unlearned authors).")
        except Exception as e:
            logger.error(f"[GLOBAL_UNLEARNING] Failed loading registry: {e}")
        finally:
            conn.close()



    def record_global_unlearning(
        self,
        target_type: str,
        target_author_id: str,
        target_author_name: str,
        target_identifier: str,
        qa_ids: List[str],
        request_id: Optional[str] = None,
    ) -> None:
        \"\"\"
        Persists confirmed unlearning into SQLite global_unlearning_registry and updates in-memory state.
        Instantly invalidates cached vectors and sanitizes existing chat memory across all sessions.
        \"\"\"
        now = datetime.now(timezone.utc).isoformat()
        reg_id = f"REG-{uuid.uuid4().hex[:8].upper()}"

        if target_type in ("AUTHOR", "GROUP"):
            self.unlearned_authors.add(target_author_id)
            if target_author_id in self.working_authors:
                for qa in self.working_authors[target_author_id].get("qa_pairs", []):
                    self.unlearned_qa.setdefault(target_author_id, set()).add(qa["qa_id"])
            for q in qa_ids:
                self.unlearned_qa.setdefault(target_author_id, set()).add(q)
        else:
            for q in qa_ids:
                self.unlearned_qa.setdefault(target_author_id, set()).add(q)
            if target_author_id in self.working_authors:
                total = len(self.working_authors[target_author_id].get("qa_pairs", []))
                if total > 0 and len(self.unlearned_qa.get(target_author_id, set())) >= total:
                    self.unlearned_authors.add(target_author_id)

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                INSERT OR REPLACE INTO global_unlearning_registry (
                    id, target_type, target_author_id, target_author_name,
                    target_identifier, qa_ids, request_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?)
            \"\"\", (
                reg_id,
                target_type,
                target_author_id,
                target_author_name,
                target_identifier,
                json.dumps(qa_ids),
                request_id,
                now,
                now,
            ))
            conn.commit()
        finally:
            conn.close()



        # Sanitize existing chat sessions in database so old sessions don't leak memory
        self._sanitize_existing_chat_sessions(target_author_id, qa_ids)

    def get_global_registry(self) -> List[Dict[str, Any]]:
        \"\"\"Returns all confirmed unlearning entries in the persistent global registry.\"\"\"
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM global_unlearning_registry ORDER BY updated_at DESC")
            rows = c.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                try:
                    item["qa_ids"] = json.loads(item["qa_ids"]) if item.get("qa_ids") else []
                except Exception:
                    item["qa_ids"] = []
                result.append(item)
            return result
        finally:
            conn.close()



    def _sanitize_existing_chat_sessions(self, target_author_id: str, qa_ids: List[str]) -> None:
        \"\"\"
        Sanitizes existing chat session records in SQLite to prevent stale conversation memory
        from re-surfacing unlearned information across any past or present session.
        \"\"\"
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT id, messages FROM chat_sessions")
            rows = c.fetchall()
            qa_set = set(qa_ids)

            for row in rows:
                sess_id = row["id"]
                raw_msgs = row["messages"]
                if not raw_msgs:
                    continue
                try:
                    msgs = json.loads(raw_msgs)
                except Exception:
                    continue

                modified = False
                for m in msgs:
                    if m.get("role") == "assistant":
                        sources = m.get("sources", [])
                        for s in sources:
                            if s.get("author_id") == target_author_id or s.get("source_id") in qa_set:
                                s["is_unlearned"] = True
                                s["status"] = "UNLEARNED_REDACTED"
                                s["ground_truth_answer"] = "[REDACTED PURSUANT TO GLOBAL UNLEARNING]"
                                s["confidence"] = 0.0
                                modified = True
                        if modified and not m.get("content", "").startswith("[PRIVACY ENFORCED // RECORD REDACTED]"):
                            m["content"] = (
                                f"[PRIVACY ENFORCED // RECORD REDACTED]\\n"
                                f"Information concerning author {target_author_id} has been permanently "
                                f"unlearned from the knowledge store across all chat sessions."
                            )

                if modified:
                    c.execute("UPDATE chat_sessions SET messages = ? WHERE id = ?", (json.dumps(msgs), sess_id))
            conn.commit()
        except Exception as e:
            logger.error(f"[GLOBAL_UNLEARNING] Failed to sanitize existing chat sessions: {e}")
        finally:
            conn.close()"""

replacement_registry_block = """    def load_global_registry(self) -> None:
        \"\"\"
        Loads unlearning registry grouped strictly by experiment_id.
        Prevents historical or foreign experiment deletions from contaminating new experiments or clean baseline.
        \"\"\"
        self._exp_unlearned_authors = {}
        self._exp_unlearned_qa = {}
        self._exp_unlearned_authors["exp_baseline_pristine"] = set()
        self._exp_unlearned_qa["exp_baseline_pristine"] = {}

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                SELECT * FROM global_unlearning_registry 
                WHERE status = 'CONFIRMED' AND experiment_id IS NOT NULL AND experiment_id != 'exp_legacy_isolated'
            \"\"\" )
            rows = c.fetchall()

            for row in rows:
                exp_id = row["experiment_id"]
                target_type = row["target_type"]
                author_id = row["target_author_id"]
                try:
                    qa_ids = json.loads(row["qa_ids"]) if row["qa_ids"] else []
                except Exception:
                    qa_ids = []

                self._exp_unlearned_authors.setdefault(exp_id, set())
                self._exp_unlearned_qa.setdefault(exp_id, {})

                if target_type in ("AUTHOR", "GROUP"):
                    self._exp_unlearned_authors[exp_id].add(author_id)
                    if author_id in self.working_authors:
                        for qa in self.working_authors[author_id].get("qa_pairs", []):
                            self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(qa["qa_id"])
                    for q in qa_ids:
                        self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(q)
                elif target_type in ("QA", "ATTRIBUTE"):
                    for q in qa_ids:
                        self._exp_unlearned_qa[exp_id].setdefault(author_id, set()).add(q)
                    if author_id in self.working_authors:
                        total = len(self.working_authors[author_id].get("qa_pairs", []))
                        if total > 0 and len(self._exp_unlearned_qa[exp_id].get(author_id, set())) >= total:
                            self._exp_unlearned_authors[exp_id].add(author_id)
            logger.info(f"[EXPERIMENT_REGISTRY] Loaded scoped unlearning entries for {len(self._exp_unlearned_authors)} experiments.")
        except Exception as e:
            logger.error(f"[EXPERIMENT_REGISTRY] Failed loading registry: {e}")
        finally:
            conn.close()

    def record_global_unlearning(
        self,
        target_type: str,
        target_author_id: str,
        target_author_name: str,
        target_identifier: str,
        qa_ids: List[str],
        request_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> None:
        \"\"\"
        Persists confirmed unlearning into SQLite global_unlearning_registry scoped to experiment_id.
        Updates experiment in-memory state and sanitizes chat sessions belonging to that experiment.
        \"\"\"
        norm_aid = self._normalize_author_id(target_author_id)
        exp_id = self.resolve_experiment_id(experiment_id)
        now = datetime.now(timezone.utc).isoformat()
        reg_id = f"REG-{uuid.uuid4().hex[:8].upper()}"

        self._exp_unlearned_authors.setdefault(exp_id, set())
        self._exp_unlearned_qa.setdefault(exp_id, {})

        if target_type in ("AUTHOR", "GROUP"):
            self._exp_unlearned_authors[exp_id].add(norm_aid)
            if norm_aid in self.working_authors:
                for qa in self.working_authors[norm_aid].get("qa_pairs", []):
                    self._exp_unlearned_qa[exp_id].setdefault(norm_aid, set()).add(qa["qa_id"])
            for q in qa_ids:
                self._exp_unlearned_qa[exp_id].setdefault(norm_aid, set()).add(q)
        else:
            for q in qa_ids:
                self._exp_unlearned_qa[exp_id].setdefault(norm_aid, set()).add(q)
            if norm_aid in self.working_authors:
                total = len(self.working_authors[norm_aid].get("qa_pairs", []))
                if total > 0 and len(self._exp_unlearned_qa[exp_id].get(norm_aid, set())) >= total:
                    self._exp_unlearned_authors[exp_id].add(norm_aid)

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                INSERT OR REPLACE INTO global_unlearning_registry (
                    id, target_type, target_author_id, target_author_name,
                    target_identifier, qa_ids, request_id, experiment_id,
                    dataset_version, knowledge_store_version, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v1.0-clean', 'v1.0-clean', 'CONFIRMED', ?, ?)
            \"\"\", (
                reg_id,
                target_type,
                norm_aid,
                target_author_name,
                target_identifier,
                json.dumps(qa_ids),
                request_id,
                exp_id,
                now,
                now,
            ))
            conn.commit()
        finally:
            conn.close()

        # Sanitize chat sessions belonging to this experiment
        self._sanitize_existing_chat_sessions(norm_aid, qa_ids, experiment_id=exp_id)

    def get_global_registry(self, experiment_id: Optional[str] = None) -> List[Dict[str, Any]]:
        \"\"\"Returns confirmed unlearning entries in persistent registry, optionally scoped by experiment_id.\"\"\"
        conn = get_db_connection()
        try:
            c = conn.cursor()
            if experiment_id and experiment_id.strip():
                c.execute("SELECT * FROM global_unlearning_registry WHERE experiment_id = ? ORDER BY updated_at DESC", (experiment_id.strip(),))
            else:
                c.execute("SELECT * FROM global_unlearning_registry ORDER BY updated_at DESC")
            rows = c.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                try:
                    item["qa_ids"] = json.loads(item["qa_ids"]) if item.get("qa_ids") else []
                except Exception:
                    item["qa_ids"] = []
                result.append(item)
            return result
        finally:
            conn.close()

    def _sanitize_existing_chat_sessions(self, target_author_id: str, qa_ids: List[str], experiment_id: Optional[str] = None) -> None:
        \"\"\"
        Sanitizes existing chat session records in SQLite scoped to this experiment.
        \"\"\"
        exp_id = self.resolve_experiment_id(experiment_id)
        conn = get_db_connection()
        try:
            c = conn.cursor()
            if exp_id and exp_id != "default_experiment":
                c.execute("SELECT id, messages FROM chat_sessions WHERE experiment_id = ?", (exp_id,))
            else:
                c.execute("SELECT id, messages FROM chat_sessions WHERE experiment_id = ? OR experiment_id IS NULL", (exp_id,))
            rows = c.fetchall()
            qa_set = set(qa_ids)

            for row in rows:
                sess_id = row["id"]
                raw_msgs = row["messages"]
                if not raw_msgs:
                    continue
                try:
                    msgs = json.loads(raw_msgs)
                except Exception:
                    continue

                modified = False
                for m in msgs:
                    if m.get("role") == "assistant":
                        sources = m.get("sources", [])
                        for s in sources:
                            if s.get("author_id") == target_author_id or s.get("source_id") in qa_set:
                                s["is_unlearned"] = True
                                s["status"] = "UNLEARNED_REDACTED"
                                s["ground_truth_answer"] = "[REDACTED PURSUANT TO EXPERIMENT UNLEARNING]"
                                s["confidence"] = 0.0
                                modified = True
                        if modified and not m.get("content", "").startswith("[PRIVACY ENFORCED // RECORD REDACTED]"):
                            m["content"] = (
                                f"[PRIVACY ENFORCED // RECORD REDACTED]\\n"
                                f"Information concerning author {target_author_id} has been permanently "
                                f"unlearned in this experiment's active knowledge store."
                            )

                if modified:
                    c.execute("UPDATE chat_sessions SET messages = ? WHERE id = ?", (json.dumps(msgs), sess_id))
            conn.commit()
        except Exception as e:
            logger.error(f"[EXPERIMENT_UNLEARNING] Failed to sanitize existing chat sessions for {exp_id}: {e}")
        finally:
            conn.close()"""

assert target_registry_block in code, "Target registry block not found"
code = code.replace(target_registry_block, replacement_registry_block, 1)

print("Sections 1 & 2 replaced successfully")
with open("scratch/patched_stage1.py", "w", encoding="utf-8") as f:
    f.write(code)
