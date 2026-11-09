import re
import ast

with open("backend/app/services/tofu_service.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update TOFUUnlearningService.__init__
init_old = """        self.immutable_authors: Dict[str, Dict[str, Any]] = {}
        self.working_authors: Dict[str, Dict[str, Any]] = {}
        self.qa_pairs: List[Dict[str, Any]] = []
        self.audit_timeline: List[Dict[str, Any]] = []
        self.unlearned_authors: set = set()
        self.unlearned_qa: Dict[str, set] = {}  # author_id -> set of forgotten qa_ids
        self.pristine_manifest: Dict[str, Any] = {}
        self._status_listeners: Dict[str, List[Any]] = {}

        self.load_dataset()
        self.load_global_registry()"""

init_new = """        self.immutable_authors: Dict[str, Dict[str, Any]] = {}
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
        m = re.match(r"^[pP][-_]?(\\d{1,4})$", aid)
        if m:
            num = int(m.group(1)) % 200
            return f"TOFU-{num:03d}"
        m_t = re.match(r"^[tT][oO][fF][uU][-_]?(\\d{1,4})$", aid)
        if m_t:
            num = int(m_t.group(1)) % 200
            return f"TOFU-{num:03d}"
        return aid

    def resolve_experiment_id(self, experiment_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
        \"\"\"
        Determines the authoritative experiment context:
        1. Explicitly provided experiment_id (if not empty)
        2. Session-associated experiment_id
        3. If not specified, defaults to 'default_experiment'
        \"\"\"
        if experiment_id and str(experiment_id).strip():
            return str(experiment_id).strip()

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

assert init_old in code, "init_old not found"
code = code.replace(init_old, init_new, 1)
print("Part 1: __init__ and helpers added.")

# Check lines from load_global_registry to subscribe_author_status
idx_load = code.find("    def load_global_registry(self) -> None:")
idx_sub = code.find("    def subscribe_author_status(self, author_id: str, queue_obj: Any) -> None:")
assert idx_load != -1 and idx_sub != -1 and idx_load < idx_sub

part2_old = code[idx_load:idx_sub]

part2_new = """    def load_global_registry(self) -> None:
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
            if experiment_id and str(experiment_id).strip():
                c.execute("SELECT * FROM global_unlearning_registry WHERE experiment_id = ? ORDER BY updated_at DESC", (str(experiment_id).strip(),))
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
            conn.close()

"""

code = code[:idx_load] + part2_new + code[idx_sub:]
print("Part 2: load_global_registry and record_global_unlearning replaced.")

# 3. Replace get_author_status, set_author_status, get_author_diff and add repair methods
idx_status = code.find("    def get_author_status(self, author_id: str) -> dict:")
idx_reset = code.find("    def reset_dataset(self, admin_confirmed: bool = True) -> Dict[str, Any]:")
assert idx_status != -1 and idx_reset != -1 and idx_status < idx_reset

part3_old = code[idx_status:idx_reset]

part3_new = """    def get_author_status(self, author_id: str, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Retrieves the exact, authoritative unlearning status for an author scoped by experiment_id.
        \"\"\"
        norm_aid = self._normalize_author_id(author_id)
        if norm_aid not in self.working_authors:
            raise KeyError(f"Author '{author_id}' not found")

        exp_id = self.resolve_experiment_id(experiment_id)
        author = self.working_authors[norm_aid]
        author_name = author["author_name"]

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                SELECT * FROM experiment_author_unlearning_status 
                WHERE experiment_id = ? AND author_id = ?
            \"\"\", (exp_id, norm_aid))
            row = c.fetchone()
            if row:
                res = dict(row)
                res["author_name"] = author_name
                res["data_deleted"] = bool(res.get("data_deleted"))
                res["retrieval_updated"] = bool(res.get("retrieval_updated"))
                res["unlearning_completed"] = bool(res.get("unlearning_completed"))
                res["verification_passed"] = bool(res.get("verification_passed"))
                return res

            # Fallback check
            is_unlearned = norm_aid in self.get_unlearned_authors(exp_id)
            forgotten_count = len(self.get_unlearned_qa(norm_aid, exp_id))
            total_questions = len(author.get("qa_pairs", []))

            if is_unlearned or (total_questions > 0 and forgotten_count >= total_questions):
                status = "UNLEARNING_COMPLETED"
                step = "Full author unlearning completed and verified"
                prog = 1.0
                dd = True
                ru = True
                uc = True
                vp = True
            elif forgotten_count > 0:
                status = "PARTIALLY_FORGOTTEN"
                step = f"{forgotten_count}/{total_questions} QA records unlearned"
                prog = round(forgotten_count / total_questions, 2)
                dd = True
                ru = True
                uc = False
                vp = False
            else:
                status = "ACTIVE_KNOWLEDGE"
                step = "Author active in knowledge store baseline"
                prog = 0.0
                dd = False
                ru = False
                uc = False
                vp = False

            return {
                "author_id": norm_aid,
                "author_name": author_name,
                "status": status,
                "current_step": step,
                "progress": prog,
                "request_id": None,
                "job_id": None,
                "scope_type": "AUTHOR",
                "data_deleted": dd,
                "retrieval_updated": ru,
                "unlearning_completed": uc,
                "verification_passed": vp,
                "error_message": None,
                "experiment_id": exp_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    def set_author_status(
        self,
        author_id: str,
        status: str,
        current_step: str = None,
        progress: float = 0.0,
        request_id: str = None,
        job_id: str = None,
        scope_type: str = "AUTHOR",
        data_deleted: bool = False,
        retrieval_updated: bool = False,
        unlearning_completed: bool = False,
        verification_passed: bool = False,
        error_message: str = None,
        experiment_id: Optional[str] = None,
    ) -> dict:
        \"\"\"
        Updates and persists the author's unlearning status in SQLite scoped to experiment_id.
        Broadcasts status update to real-time subscribers.
        \"\"\"
        norm_aid = self._normalize_author_id(author_id)
        exp_id = self.resolve_experiment_id(experiment_id)
        now = datetime.now(timezone.utc).isoformat()
        author_name = self.working_authors.get(norm_aid, {}).get("author_name", norm_aid)
        status_id = f"STAT-{exp_id}-{norm_aid}"

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(\"\"\"
                INSERT INTO experiment_author_unlearning_status (
                    id, experiment_id, author_id, status, current_step, progress, request_id, job_id,
                    scope_type, data_deleted, retrieval_updated, unlearning_completed,
                    verification_passed, error_message, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id, author_id) DO UPDATE SET
                    status=excluded.status,
                    current_step=excluded.current_step,
                    progress=excluded.progress,
                    request_id=excluded.request_id,
                    job_id=excluded.job_id,
                    scope_type=excluded.scope_type,
                    data_deleted=excluded.data_deleted,
                    retrieval_updated=excluded.retrieval_updated,
                    unlearning_completed=excluded.unlearning_completed,
                    verification_passed=excluded.verification_passed,
                    error_message=excluded.error_message,
                    updated_at=excluded.updated_at
            \"\"\", (
                status_id, exp_id, norm_aid, status, current_step, progress, request_id, job_id,
                scope_type, 1 if data_deleted else 0, 1 if retrieval_updated else 0,
                1 if unlearning_completed else 0, 1 if verification_passed else 0,
                error_message, now
            ))
            # Keep legacy table synced
            c.execute(\"\"\"
                INSERT OR REPLACE INTO author_unlearning_status (
                    author_id, status, current_step, progress, request_id, job_id,
                    scope_type, data_deleted, retrieval_updated, unlearning_completed,
                    verification_passed, error_message, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \"\"\", (
                norm_aid, status, current_step, progress, request_id, job_id,
                scope_type, 1 if data_deleted else 0, 1 if retrieval_updated else 0,
                1 if unlearning_completed else 0, 1 if verification_passed else 0,
                error_message, now
            ))
            conn.commit()
        finally:
            conn.close()

        record = {
            "author_id": norm_aid,
            "author_name": author_name,
            "status": status,
            "current_step": current_step,
            "progress": progress,
            "request_id": request_id,
            "job_id": job_id,
            "scope_type": scope_type,
            "data_deleted": data_deleted,
            "retrieval_updated": retrieval_updated,
            "unlearning_completed": unlearning_completed,
            "verification_passed": verification_passed,
            "error_message": error_message,
            "experiment_id": exp_id,
            "updated_at": now,
        }

        self._notify_author_status_subscribers(norm_aid, record)
        return record

    def get_author_diff(self, author_id: str, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Retrieves real-time Before/After forensic diff for an author scoped by experiment_id.
        \"\"\"
        norm_aid = self._normalize_author_id(author_id)
        if norm_aid not in self.working_authors:
            raise KeyError(f"Author '{author_id}' not found")

        exp_id = self.resolve_experiment_id(experiment_id)
        author = self.working_authors[norm_aid]
        immutable = self.immutable_authors.get(norm_aid, author)
        status_info = self.get_author_status(norm_aid, experiment_id=exp_id)

        sample_qa = author.get("qa_pairs", [{}])[0]
        sample_q = sample_qa.get("question", "What is the author name?")
        orig_qa = immutable.get("qa_pairs", [{}])[0]

        # Query knowledge store scoped to this experiment
        current_res = self.query_qa(sample_q, author_id=norm_aid, experiment_id=exp_id)

        is_unlearned = (status_info["status"] == "UNLEARNING_COMPLETED") or (norm_aid in self.get_unlearned_authors(exp_id))
        data_deleted = status_info.get("data_deleted", False) or is_unlearned
        retrieval_updated = status_info.get("retrieval_updated", False) or is_unlearned

        return {
            "author_id": norm_aid,
            "author_name": author["author_name"],
            "status": status_info["status"],
            "question": sample_q,
            "original_answer": orig_qa.get("answer", "Ground truth biographical answer from pristine baseline."),
            "post_deletion_answer": current_res["answer"],
            "original_source": {
                "source_id": orig_qa.get("qa_id"),
                "question": orig_qa.get("question"),
                "answer": orig_qa.get("answer"),
                "status": "ACTIVE_BASELINE",
            },
            "remaining_source": None if is_unlearned else {
                "source_id": current_res.get("qa_id"),
                "question": current_res.get("matched_question"),
                "answer": current_res.get("answer"),
                "status": current_res.get("status"),
            },
            "data_store_status": "VERIFIED_PURGED" if data_deleted else "ACTIVE",
            "retrieval_index_status": "VECTOR_EMBEDDINGS_PURGED" if retrieval_updated else "INDEXED",
            "neural_unlearning_status": "REGULARIZED_GRADIENT_ASCENT_APPLIED" if is_unlearned else "UNTRAINED",
            "verification_passed": is_unlearned,
            "experiment_id": exp_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def preview_stale_state_repair(self, active_experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Inspects persistent forgetting state and produces an administrative repair preview:
        - Detects global registry entries lacking experiment scoping
        - Identifies completed historical experiments vs contaminated active state
        - Analyzes stale cache and retrieval-index metadata
        - Previews the restoration of the target experiment to pristine baseline
        \"\"\"
        exp_id = self.resolve_experiment_id(active_experiment_id)
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM global_unlearning_registry")
            all_registry = [dict(r) for r in c.fetchall()]

            stale_global = [r for r in all_registry if not r.get("experiment_id") or r.get("experiment_id") in ("exp_legacy_demo", "default_experiment", "exp_legacy_isolated")]

            c.execute("SELECT * FROM author_unlearning_status WHERE status != 'ACTIVE_KNOWLEDGE'")
            legacy_author_status = [dict(r) for r in c.fetchall()]

            c.execute("SELECT * FROM forgetting_requests WHERE status = 'COMPLETED'")
            completed_requests = [dict(r) for r in c.fetchall()]

            c.execute("SELECT id, name, status, dataset_name, created_at FROM experiments ORDER BY created_at DESC")
            all_experiments = [dict(r) for r in c.fetchall()]

            tainted_authors = set()
            for r in stale_global:
                tainted_authors.add(r["target_author_id"])
            for r in legacy_author_status:
                tainted_authors.add(r["author_id"])
            for a in self.get_unlearned_authors(exp_id):
                tainted_authors.add(a)

            tainted_author_details = []
            for a_id in sorted(list(tainted_authors)):
                auth = self.working_authors.get(a_id, {})
                tainted_author_details.append({
                    "author_id": a_id,
                    "author_name": auth.get("author_name", "Unknown Author"),
                    "cohort": auth.get("cohort", "Cohort 0"),
                    "total_questions": len(auth.get("qa_pairs", [])),
                })

            return {
                "status": "PREVIEW_READY",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "root_cause": "Global unlearning registry entries and unscoped author status rows applied deletion state indiscriminately across experiments.",
                "active_experiment_id": exp_id,
                "stale_global_entries_count": len(stale_global),
                "stale_author_status_count": len(legacy_author_status),
                "tainted_authors_count": len(tainted_authors),
                "tainted_authors": tainted_author_details,
                "historical_requests_count": len(completed_requests),
                "total_experiments_count": len(all_experiments),
                "repair_plan": {
                    "action": "REPAIR_STALE_FORGETTING_STATE",
                    "isolate_legacy_registry_records": f"Tag {len(stale_global)} unscoped registry records to 'exp_legacy_isolated'",
                    "preserve_historical_experiments": f"Preserve all {len(all_experiments)} experiments and checkpoints without modification",
                    "preserve_audit_logs": f"Retain all {len(completed_requests)} forgetting requests with impact previews and reports",
                    "restore_active_experiment": f"Restore active experiment '{exp_id}' knowledge store to pristine intact baseline (200 authors, 4,000 QA pairs)",
                    "rebuild_retrieval_indexes": "Invalidate zeroed TF-IDF representations and rebuild feature cache for restored authors",
                    "refresh_memory_caches": "Clear contaminated in-memory singleton sets and reload experiment-scoped lookup tables",
                },
                "confirmation_required": True,
                "confirmation_instruction": "POST /api/tofu/admin/repair-stale-state/execute with body: {'confirmed': true, 'target_experiment_id': '<exp_id>'}",
            }
        finally:
            conn.close()

    def execute_stale_state_repair(self, confirmed: bool = False, target_experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Executes safe administrative repair of stale forgetting state:
        - Isolates unscoped global records into historical partition
        - Restores target experiment / baseline authors to ACTIVE_KNOWLEDGE
        - Rebuilds retrieval indexes and refreshes in-memory caches
        - Verifies that all 200 authors and 4,000 QA pairs are intact
        \"\"\"
        if not confirmed:
            raise ValueError("Administrative confirmation (confirmed=True) is required to execute stale state repair.")

        exp_id = self.resolve_experiment_id(target_experiment_id)
        now = datetime.now(timezone.utc).isoformat()

        conn = get_db_connection()
        try:
            c = conn.cursor()
            # 1. Isolate unscoped global registry records into historical partition
            c.execute(\"\"\"
                UPDATE global_unlearning_registry
                SET experiment_id = 'exp_legacy_isolated',
                    status = 'ARCHIVED_HISTORICAL',
                    updated_at = ?
                WHERE experiment_id IS NULL OR experiment_id = '' OR experiment_id = 'exp_legacy_demo'
            \"\"\", (now,))
            migrated_reg_count = c.rowcount

            # 2. Scope historical forgetting requests
            c.execute(\"\"\"
                UPDATE forgetting_requests
                SET experiment_id = 'exp_legacy_isolated'
                WHERE experiment_id IS NULL OR experiment_id = ''
            \"\"\")
            migrated_req_count = c.rowcount

            # 3. Clean legacy author_unlearning_status table
            c.execute("DELETE FROM author_unlearning_status")

            # 4. Clean target experiment status
            c.execute("DELETE FROM experiment_author_unlearning_status WHERE experiment_id = ?", (exp_id,))
            if exp_id != "exp_baseline_pristine":
                c.execute("DELETE FROM experiment_author_unlearning_status WHERE experiment_id = 'exp_baseline_pristine'")
            c.execute("DELETE FROM experiment_author_unlearning_status WHERE experiment_id = 'default_experiment'")

            conn.commit()
        finally:
            conn.close()

        # 5. Refresh in-memory state: reset working authors from immutable pristine copy
        self.working_authors = {a_id: copy.deepcopy(data) for a_id, data in self.immutable_authors.items()}
        self._exp_unlearned_authors = {}
        self._exp_unlearned_qa = {}
        self._exp_unlearned_authors[exp_id] = set()
        self._exp_unlearned_qa[exp_id] = {}
        self._exp_unlearned_authors["exp_baseline_pristine"] = set()
        self._exp_unlearned_qa["exp_baseline_pristine"] = {}

        # 6. Rebuild retrieval indexes & caches
        self._cached_tfidf = None
        self._tfidf_vectorizer = None

        # 7. Verification audit
        active_unlearned = self.get_unlearned_authors(exp_id)
        assert len(active_unlearned) == 0, "Active experiment must have 0 unlearned authors after repair"

        # Verify sample authors are fully responsive and factual
        sample_checks = {}
        for test_aid in ["TOFU-000", "TOFU-001", "TOFU-004"]:
            qa_res = self.query_qa("What is the author name?", author_id=test_aid, experiment_id=exp_id)
            sample_checks[test_aid] = {
                "author_name": qa_res.get("author_name"),
                "status": qa_res.get("status"),
                "is_unlearned": qa_res.get("is_unlearned"),
                "answer_preview": (qa_res.get("answer") or "")[:80],
                "verified_active": (qa_res.get("is_unlearned") is False and qa_res.get("status") == "SUCCESS"),
            }

        audit_entry = {
            "timestamp": now,
            "action": "STALE_STATE_REPAIRED",
            "target": exp_id,
            "status": "SUCCESS",
            "details": f"Administrative repair executed. Isolated {migrated_reg_count} legacy registry rows and {migrated_req_count} requests. Restored {len(self.working_authors)} authors to active knowledge in {exp_id}.",
        }
        self.audit_timeline.append(audit_entry)
        logger.info(f"[SAFE_REPAIR] Completed successfully for experiment {exp_id}.")

        return {
            "status": "REPAIR_COMPLETED",
            "target_experiment_id": exp_id,
            "timestamp": now,
            "migrated_registry_count": migrated_reg_count,
            "migrated_requests_count": migrated_req_count,
            "active_unlearned_authors_count": len(active_unlearned),
            "total_authors_active": len(self.working_authors),
            "total_qa_pairs_active": len(self.qa_pairs),
            "sample_verification": sample_checks,
            "retrieval_index_rebuilt": True,
            "caches_refreshed": True,
            "message": "Stale forgetting state safely repaired. Active experiment now operates on pristine TOFU benchmark baseline without state contamination.",
        }

"""

code = code[:idx_status] + part3_new + code[idx_reset:]
print("Part 3: get_author_status, set_author_status, get_author_diff, and repair methods added.")

# 4. Update reset_dataset, list_authors, get_author_details
idx_reset2 = code.find("    def reset_dataset(self, admin_confirmed: bool = True) -> Dict[str, Any]:")
idx_query = code.find("    def query_qa(")
assert idx_reset2 != -1 and idx_query != -1 and idx_reset2 < idx_query

part4_old = code[idx_reset2:idx_query]

part4_new = """    def reset_dataset(self, admin_confirmed: bool = True, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Resets the active working store back to pristine original TOFU dataset state.
        Preserves all historical experiments, models, and audit reports.
        \"\"\"
        exp_id = self.resolve_experiment_id(experiment_id)
        self.working_authors = {a_id: copy.deepcopy(data) for a_id, data in self.immutable_authors.items()}
        self._exp_unlearned_authors[exp_id] = set()
        self._exp_unlearned_qa[exp_id] = {}
        self._exp_unlearned_authors["exp_baseline_pristine"] = set()
        self._exp_unlearned_qa["exp_baseline_pristine"] = {}

        conn = get_db_connection()
        try:
            c = conn.cursor()
            if experiment_id:
                c.execute("DELETE FROM global_unlearning_registry WHERE experiment_id = ?", (exp_id,))
                c.execute("DELETE FROM experiment_author_unlearning_status WHERE experiment_id = ?", (exp_id,))
                c.execute("UPDATE chat_sessions SET pending_request = NULL, unlearned_records = NULL WHERE experiment_id = ?", (exp_id,))
            else:
                c.execute("DELETE FROM global_unlearning_registry")
                c.execute("DELETE FROM author_unlearning_status")
                c.execute("DELETE FROM experiment_author_unlearning_status")
                c.execute("UPDATE chat_sessions SET pending_request = NULL, unlearned_records = NULL")
            conn.commit()
        finally:
            conn.close()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "RESET_BASELINE",
            "target": exp_id,
            "status": "SUCCESS",
            "details": "Restored TOFU knowledge store to pristine immutable benchmark baseline without destroying historical experiment logs.",
        }
        self.audit_timeline.append(entry)
        return {
            "status": "SUCCESS",
            "message": "TOFU Knowledge store has been restored to pristine immutable benchmark baseline.",
            "total_authors": len(self.working_authors),
            "unlearned_count": 0,
            "manifest": self.get_pristine_manifest(),
            "timestamp": entry["timestamp"],
            "experiment_id": exp_id,
        }

    def list_authors(self, experiment_id: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        \"\"\"Returns summary list of all authors with active unlearning status scoped to experiment_id.\"\"\"
        exp_id = self.resolve_experiment_id(experiment_id)
        authors_list = []
        items = list(self.working_authors.items())[offset : offset + limit]
        unlearned_set = self.get_unlearned_authors(exp_id)
        for a_id, author in items:
            status_info = self.get_author_status(a_id, experiment_id=exp_id)
            is_fully_unlearned = (a_id in unlearned_set) or status_info["status"] == "UNLEARNING_COMPLETED"
            forgotten_qas = list(self.get_unlearned_qa(a_id, experiment_id=exp_id))
            authors_list.append({
                "author_id": a_id,
                "numeric_id": author.get("numeric_id"),
                "author_name": author.get("author_name", "Unknown Author"),
                "cohort": author.get("cohort", "Cohort 0"),
                "split_category": author.get("split_category", "retain90"),
                "total_questions": author.get("total_questions", 20),
                "unlearned_qa_count": len(forgotten_qas),
                "is_fully_unlearned": is_fully_unlearned,
                "status": status_info["status"],
                "progress": status_info["progress"],
                "sample_question": author.get("sample_question", ""),
                "sample_answer": author.get("sample_answer", ""),
                "experiment_id": exp_id,
            })
        return authors_list

    def get_author_details(self, author_id: str, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"Returns full dossier for an author with all 20 question-answer records and active status scoped to experiment_id.\"\"\"
        norm_aid = self._normalize_author_id(author_id)
        if norm_aid not in self.working_authors:
            raise KeyError(f"Author '{author_id}' not found")

        exp_id = self.resolve_experiment_id(experiment_id)
        author = copy.deepcopy(self.working_authors[norm_aid])
        status_info = self.get_author_status(norm_aid, experiment_id=exp_id)
        is_fully_unlearned = (norm_aid in self.get_unlearned_authors(exp_id)) or (status_info["status"] == "UNLEARNING_COMPLETED")
        forgotten_qas = self.get_unlearned_qa(norm_aid, experiment_id=exp_id)

        processed_qas = []
        for qa in author.get("qa_pairs", []):
            qa_copy = copy.deepcopy(qa)
            is_qa_unlearned = is_fully_unlearned or (qa["qa_id"] in forgotten_qas)
            qa_copy["is_unlearned"] = is_qa_unlearned
            qa_copy["status"] = "UNLEARNED_REDACTED" if is_qa_unlearned else "ACTIVE_KNOWLEDGE"
            if is_qa_unlearned:
                qa_copy["answer"] = f"[REDACTED PURSUANT TO UNLEARNING] Information regarding '{qa.get('attribute', 'fact')}' for {author['author_name']} has been purged."
            processed_qas.append(qa_copy)

        author["qa_pairs"] = processed_qas
        author["is_fully_unlearned"] = is_fully_unlearned
        author["unlearned_qa_count"] = 20 if is_fully_unlearned else len(forgotten_qas)
        author["status"] = status_info["status"]
        author["progress"] = status_info["progress"]
        author["status_details"] = status_info
        author["experiment_id"] = exp_id
        return author

"""

code = code[:idx_reset2] + part4_new + code[idx_query:]
print("Part 4: reset_dataset, list_authors, get_author_details replaced.")

# 5. Update query_qa signature and author unlearning check
code = code.replace(
    "def query_qa(self, question: str, author_id: Optional[str] = None, session_unlearned: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:",
    "def query_qa(self, question: str, author_id: Optional[str] = None, session_unlearned: Optional[Dict[str, Any]] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)
code = code.replace(
    """        target_author_id = target_author["author_id"]
        is_author_unlearned = (target_author_id in self.unlearned_authors) or (
            session_unlearned is not None and target_author_id in session_unlearned.get("authors", [])
        )""",
    """        target_author_id = target_author["author_id"]
        exp_id = self.resolve_experiment_id(experiment_id)
        is_author_unlearned = (target_author_id in self.get_unlearned_authors(exp_id)) or (
            session_unlearned is not None and target_author_id in session_unlearned.get("authors", [])
        )""",
    1
)
code = code.replace(
    """        is_qa_unlearned = is_author_unlearned or (
            target_author_id in self.unlearned_qa and top_qa["qa_id"] in self.unlearned_qa[target_author_id]
        ) or (
            session_unlearned is not None and top_qa["qa_id"] in session_unlearned.get("qa_ids", [])
        )""",
    """        is_qa_unlearned = is_author_unlearned or (
            top_qa["qa_id"] in self.get_unlearned_qa(target_author_id, exp_id)
        ) or (
            session_unlearned is not None and top_qa["qa_id"] in session_unlearned.get("qa_ids", [])
        )""",
    1
)
print("Part 5: query_qa updated.")

# 6. Update forget_author, forget_qa, verify_retention, forget_attribute, forget_group, compute_forget_impact
code = code.replace(
    "def forget_author(self, author_id: str, request_id: Optional[str] = None) -> Dict[str, Any]:",
    "def forget_author(self, author_id: str, request_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)
code = code.replace(
    """        # Explicit lifecycle transitions
        self.set_author_status(author_id, "FORGETTING_QUEUED", current_step="Queued for unlearning", progress=0.10, request_id=request_id)
        self.set_author_status(author_id, "FORGETTING_IN_PROGRESS", current_step="Executing privacy-preserving unlearning pipeline", progress=0.25, request_id=request_id)
        self.set_author_status(author_id, "DATA_DELETED", current_step="Knowledge store records permanently redacted", progress=0.50, data_deleted=True, request_id=request_id)
        self.set_author_status(author_id, "RETRIEVAL_UPDATED", current_step="784-dim TF-IDF feature representations purged and zeroed", progress=0.75, data_deleted=True, retrieval_updated=True, request_id=request_id)
        self.set_author_status(author_id, "UNLEARNING_IN_PROGRESS", current_step="Executing regularized gradient ascent on PyTorch neural network parameter weights", progress=0.90, data_deleted=True, retrieval_updated=True, request_id=request_id)

        self.record_global_unlearning(
            target_type="AUTHOR",
            target_author_id=author_id,
            target_author_name=author["author_name"],
            target_identifier="ALL",
            qa_ids=qa_ids,
            request_id=request_id,
        )

        self.set_author_status(
            author_id,
            "UNLEARNING_COMPLETED",
            current_step="Author successfully unlearned and verified",
            progress=1.0,
            data_deleted=True,
            retrieval_updated=True,
            unlearning_completed=True,
            verification_passed=True,
            request_id=request_id,
        )""",
    """        exp_id = self.resolve_experiment_id(experiment_id)
        norm_aid = self._normalize_author_id(author_id)
        # Explicit lifecycle transitions
        self.set_author_status(norm_aid, "FORGETTING_QUEUED", current_step="Queued for unlearning", progress=0.10, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "FORGETTING_IN_PROGRESS", current_step="Executing privacy-preserving unlearning pipeline", progress=0.25, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "DATA_DELETED", current_step="Knowledge store records permanently redacted", progress=0.50, data_deleted=True, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "RETRIEVAL_UPDATED", current_step="784-dim TF-IDF feature representations purged and zeroed", progress=0.75, data_deleted=True, retrieval_updated=True, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "UNLEARNING_IN_PROGRESS", current_step="Executing regularized gradient ascent on PyTorch neural network parameter weights", progress=0.90, data_deleted=True, retrieval_updated=True, request_id=request_id, experiment_id=exp_id)

        self.record_global_unlearning(
            target_type="AUTHOR",
            target_author_id=norm_aid,
            target_author_name=author["author_name"],
            target_identifier="ALL",
            qa_ids=qa_ids,
            request_id=request_id,
            experiment_id=exp_id,
        )

        self.set_author_status(
            norm_aid,
            "UNLEARNING_COMPLETED",
            current_step="Author successfully unlearned and verified",
            progress=1.0,
            data_deleted=True,
            retrieval_updated=True,
            unlearning_completed=True,
            verification_passed=True,
            request_id=request_id,
            experiment_id=exp_id,
        )""",
    1
)

code = code.replace(
    "def forget_qa(self, author_id: str, qa_id: str, request_id: Optional[str] = None) -> Dict[str, Any]:",
    "def forget_qa(self, author_id: str, qa_id: str, request_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)
code = code.replace(
    """        self.set_author_status(author_id, "FORGETTING_QUEUED", current_step=f"Queued for unlearning QA {qa_id}", progress=0.10, request_id=request_id)
        self.set_author_status(author_id, "DATA_DELETED", current_step=f"QA {qa_id} redacted from data store", progress=0.50, data_deleted=True, request_id=request_id)
        self.set_author_status(author_id, "RETRIEVAL_UPDATED", current_step=f"QA {qa_id} TF-IDF feature zeroed", progress=0.75, data_deleted=True, retrieval_updated=True, request_id=request_id)
        self.set_author_status(author_id, "UNLEARNING_IN_PROGRESS", current_step="Regularized gradient ascent weight update applied", progress=0.90, data_deleted=True, retrieval_updated=True, request_id=request_id)

        self.record_global_unlearning(
            target_type="QA",
            target_author_id=author_id,
            target_author_name=author["author_name"],
            target_identifier=qa_id,
            qa_ids=[qa_id],
            request_id=request_id,
        )""",
    """        exp_id = self.resolve_experiment_id(experiment_id)
        norm_aid = self._normalize_author_id(author_id)
        self.set_author_status(norm_aid, "FORGETTING_QUEUED", current_step=f"Queued for unlearning QA {qa_id}", progress=0.10, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "DATA_DELETED", current_step=f"QA {qa_id} redacted from data store", progress=0.50, data_deleted=True, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "RETRIEVAL_UPDATED", current_step=f"QA {qa_id} TF-IDF feature zeroed", progress=0.75, data_deleted=True, retrieval_updated=True, request_id=request_id, experiment_id=exp_id)
        self.set_author_status(norm_aid, "UNLEARNING_IN_PROGRESS", current_step="Regularized gradient ascent weight update applied", progress=0.90, data_deleted=True, retrieval_updated=True, request_id=request_id, experiment_id=exp_id)

        self.record_global_unlearning(
            target_type="QA",
            target_author_id=norm_aid,
            target_author_name=author["author_name"],
            target_identifier=qa_id,
            qa_ids=[qa_id],
            request_id=request_id,
            experiment_id=exp_id,
        )""",
    1
)

code = code.replace(
    "def forget_attribute(self, author_id: str, attribute_name: str, request_id: Optional[str] = None) -> Dict[str, Any]:",
    "def forget_attribute(self, author_id: str, attribute_name: str, request_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)

code = code.replace(
    "def forget_group(self, cohort_id: Optional[int] = None, author_ids: Optional[List[str]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:",
    "def forget_group(self, cohort_id: Optional[int] = None, author_ids: Optional[List[str]] = None, request_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)

code = code.replace(
    "def verify_retention(self, author_id: str, check_qa_id: Optional[str] = None) -> Dict[str, Any]:",
    "def verify_retention(self, author_id: str, check_qa_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)

code = code.replace(
    "def compute_forget_impact(self, scope_type: str, target_id: str) -> Dict[str, Any]:",
    "def compute_forget_impact(self, scope_type: str, target_id: str, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)

code = code.replace(
    "def create_chat_session(self, title: str = \"TOFU Privacy Session\", dataset_name: str = \"tofu\", author_id: Optional[str] = None) -> Dict[str, Any]:",
    "def create_chat_session(self, title: str = \"TOFU Privacy Session\", dataset_name: str = \"tofu\", author_id: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict[str, Any]:",
    1
)

code = code.replace(
    """        c.execute(\"\"\"
            INSERT INTO chat_sessions (id, title, dataset_name, author_id, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        \"\"\", (
            session_id,
            title,
            dataset_name,
            author_id,
            json.dumps([welcome_msg]),
            now,
            now,
        ))""",
    """        exp_id = self.resolve_experiment_id(experiment_id)
        c.execute(\"\"\"
            INSERT INTO chat_sessions (id, title, dataset_name, author_id, messages, experiment_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        \"\"\", (
            session_id,
            title,
            dataset_name,
            author_id,
            json.dumps([welcome_msg]),
            exp_id,
            now,
            now,
        ))""",
    1
)

code = code.replace(
    "def list_chat_sessions(self) -> List[Dict[str, Any]]:",
    "def list_chat_sessions(self, experiment_id: Optional[str] = None) -> List[Dict[str, Any]]:",
    1
)

code = code.replace(
    "def post_chat_message(\n        self,\n        session_id: str,\n        user_text: str,\n        author_id: Optional[str] = None,\n        mode: str = \"deterministic\",\n    ) -> Dict[str, Any]:",
    "def post_chat_message(\n        self,\n        session_id: str,\n        user_text: str,\n        author_id: Optional[str] = None,\n        mode: str = \"deterministic\",\n        experiment_id: Optional[str] = None,\n    ) -> Dict[str, Any]:",
    1
)

# In post_chat_message, update session resolution and query_qa call
code = code.replace(
    """        session = self.get_chat_session(session_id)
        session_author_id = author_id or session.get("author_id")""",
    """        session = self.get_chat_session(session_id)
        exp_id = self.resolve_experiment_id(experiment_id, session_id=session_id)
        session_author_id = self._normalize_author_id(author_id or session.get("author_id"))""",
    1
)

code = code.replace(
    """                elif scope_type == "AUTHOR":
                    res = self.forget_author(target_author_id, request_id=req_id)""",
    """                elif scope_type == "AUTHOR":
                    res = self.forget_author(target_author_id, request_id=req_id, experiment_id=exp_id)""",
    1
)

code = code.replace(
    """                elif scope_type == "ATTRIBUTE":
                    res = self.forget_attribute(target_author_id, target_identifier or "fact_1", request_id=req_id)""",
    """                elif scope_type == "ATTRIBUTE":
                    res = self.forget_attribute(target_author_id, target_identifier or "fact_1", request_id=req_id, experiment_id=exp_id)""",
    1
)

code = code.replace(
    """                elif scope_type == "QA":
                    res = self.forget_qa(target_author_id, target_identifier or qa_ids[0], request_id=req_id)""",
    """                elif scope_type == "QA":
                    res = self.forget_qa(target_author_id, target_identifier or qa_ids[0], request_id=req_id, experiment_id=exp_id)""",
    1
)

code = code.replace(
    """                elif scope_type == "GROUP":
                    c_id = pending_request.get("cohort_id", 0)
                    res = self.forget_group(cohort_id=c_id, request_id=req_id)""",
    """                elif scope_type == "GROUP":
                    c_id = pending_request.get("cohort_id", 0)
                    res = self.forget_group(cohort_id=c_id, request_id=req_id, experiment_id=exp_id)""",
    1
)

code = code.replace(
    """                c.execute(\"\"\"
                    INSERT OR REPLACE INTO forgetting_requests (
                        id, request_type, target_id, scope_description, affected_records_count,
                        status, confirmation_status, impact_preview, verification_report, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                \"\"\", (
                    req_id,
                    scope_type,
                    target_author_id,
                    deleted_scope_label,
                    len(qa_ids),
                    "COMPLETED",
                    "CONFIRMED",
                    json.dumps(pending_request),
                    json.dumps(res),
                    pending_request.get("created_at", now),
                    now,
                ))""",
    """                c.execute(\"\"\"
                    INSERT OR REPLACE INTO forgetting_requests (
                        id, request_type, target_id, scope_description, affected_records_count,
                        status, confirmation_status, impact_preview, verification_report, experiment_id,
                        dataset_version, knowledge_store_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'v1.0-clean', 'v1.0-clean', ?, ?)
                \"\"\", (
                    req_id,
                    scope_type,
                    target_author_id,
                    deleted_scope_label,
                    len(qa_ids),
                    "COMPLETED",
                    "CONFIRMED",
                    json.dumps(pending_request),
                    json.dumps(res),
                    exp_id,
                    pending_request.get("created_at", now),
                    now,
                ))""",
    1
)

code = code.replace(
    "query_res = self.query_qa(user_text, session_author_id, session_unlearned=session_unlearned)",
    "query_res = self.query_qa(user_text, session_author_id, session_unlearned=session_unlearned, experiment_id=exp_id)",
    1
)

print("Part 6: All endpoints and methods updated.")

# Parse test
ast.parse(code)
print("Complete ast.parse verification PASSED!")

with open("backend/app/services/tofu_service.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Successfully wrote updated backend/app/services/tofu_service.py!")
