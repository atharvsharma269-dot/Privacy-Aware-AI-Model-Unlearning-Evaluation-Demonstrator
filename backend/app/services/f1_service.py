import json
import os
import re
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any


class F1UnlearningService:
    """
    Service managing the Formula 1 Real Driver Knowledge Store for live unlearning demonstrations.
    Provides isolated working state, fact query matching, scoped attribute forgetting,
    retained knowledge verification, and repeatable state reset.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Base directory relative to backend
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/f1_dataset"))
            if not os.path.exists(base):
                base = os.path.abspath("./data/f1_dataset")
            self.data_dir = base
        else:
            self.data_dir = data_dir

        self.drivers_file = os.path.join(self.data_dir, "f1_drivers.json")
        self.qa_file = os.path.join(self.data_dir, "f1_qa_pairs.jsonl")

        self.immutable_drivers: Dict[str, Dict[str, Any]] = {}
        self.working_drivers: Dict[str, Dict[str, Any]] = {}
        self.qa_pairs: List[Dict[str, Any]] = []
        self.audit_timeline: List[Dict[str, Any]] = []
        self.unlearned_attributes: Dict[str, set] = {}  # driver_id -> set of forgotten attributes

        self.load_dataset()

    def load_dataset(self) -> None:
        """Loads dataset from immutable disk files into immutable cache and working copy."""
        if not os.path.exists(self.drivers_file):
            raise FileNotFoundError(f"F1 drivers dataset not found at {self.drivers_file}")

        with open(self.drivers_file, "r", encoding="utf-8") as f:
            drivers_data = json.load(f)

        self.immutable_drivers = {d["driver_id"]: copy.deepcopy(d) for d in drivers_data}
        self.working_drivers = {d["driver_id"]: copy.deepcopy(d) for d in drivers_data}
        self.unlearned_attributes = {d["driver_id"]: set() for d in drivers_data}

        self.qa_pairs = []
        if os.path.exists(self.qa_file):
            with open(self.qa_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.qa_pairs.append(json.loads(line))

        self.audit_timeline = [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "DATASET_LOADED",
                "driver_id": "ALL",
                "attribute": "ALL",
                "status": "SUCCESS",
                "details": f"Loaded {len(self.working_drivers)} drivers and {len(self.qa_pairs)} QA pairs from {os.path.basename(self.drivers_file)}.",
            }
        ]

    def reset_dataset(self) -> Dict[str, Any]:
        """Resets the working store back to the immutable original dataset state."""
        self.working_drivers = {d_id: copy.deepcopy(data) for d_id, data in self.immutable_drivers.items()}
        self.unlearned_attributes = {d_id: set() for d_id in self.immutable_drivers.keys()}

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "RESET_DEMO",
            "driver_id": "ALL",
            "attribute": "ALL",
            "status": "SUCCESS",
            "details": "Restored active knowledge store to pristine immutable source records.",
        }
        self.audit_timeline.append(entry)
        return {
            "status": "SUCCESS",
            "message": "F1 Knowledge store has been reset to original dataset state.",
            "total_drivers": len(self.working_drivers),
            "unlearned_count": 0,
            "timestamp": entry["timestamp"],
        }

    def list_drivers(self) -> List[Dict[str, Any]]:
        """Returns summary list of all drivers with active status and unlearned count."""
        drivers_list = []
        for d_id, driver in self.working_drivers.items():
            forgotten = list(self.unlearned_attributes.get(d_id, set()))
            drivers_list.append({
                "driver_id": d_id,
                "driver_name": driver.get("driver_name", "Unknown"),
                "nationality": driver.get("nationality", "Unknown"),
                "world_drivers_championships": driver.get("world_drivers_championships", 0),
                "championship_years": driver.get("championship_years", ""),
                "championship_teams": driver.get("championship_teams", ""),
                "unlearned_attributes": forgotten,
                "is_partially_unlearned": len(forgotten) > 0,
            })
        return drivers_list

    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """Returns full active and original facts for a specific driver."""
        if driver_id not in self.working_drivers:
            raise KeyError(f"Driver '{driver_id}' not found in knowledge store.")

        working = self.working_drivers[driver_id]
        immutable = self.immutable_drivers[driver_id]
        forgotten = list(self.unlearned_attributes.get(driver_id, set()))

        driver_qas = [qa for qa in self.qa_pairs if qa.get("driver_id") == driver_id]

        return {
            "driver_id": driver_id,
            "driver_name": working.get("driver_name"),
            "working_facts": working,
            "original_facts": immutable,
            "unlearned_attributes": forgotten,
            "available_qa_pairs": driver_qas,
        }

    def _match_question_attribute(self, question: str, driver_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Parses a natural language question to match driver_id, target_attribute, and expected value.
        Uses exact QA pair matches first, then fuzzy regex template matching.
        """
        clean_q = question.strip().lower()

        # 1. Direct QA pairs match
        for qa in self.qa_pairs:
            qa_q = qa["question"].strip().lower()
            if driver_id and qa["driver_id"] != driver_id:
                continue
            if qa_q == clean_q or qa_q in clean_q or clean_q in qa_q:
                return {
                    "driver_id": qa["driver_id"],
                    "driver_name": qa["driver_name"],
                    "target_attribute": qa["target_attribute"],
                    "matched_question": qa["question"],
                }

        # 2. Heuristic extraction
        target_driver_id = driver_id
        if not target_driver_id:
            for d_id, data in self.immutable_drivers.items():
                name_parts = data["driver_name"].lower().split()
                if any(part in clean_q for part in name_parts):
                    target_driver_id = d_id
                    break

        if not target_driver_id:
            return None

        driver_meta = self.immutable_drivers[target_driver_id]

        # Extract year if mentioned (e.g. 2020, 2008, 1994, 2014, 2021, etc.)
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_q)
        year = year_match.group(1) if year_match else None

        if "nationality" in clean_q or "country" in clean_q:
            return {
                "driver_id": target_driver_id,
                "driver_name": driver_meta["driver_name"],
                "target_attribute": "nationality",
                "matched_question": question,
            }

        if year:
            if "team" in clean_q:
                attr = f"team_for_{year}_title"
                return {
                    "driver_id": target_driver_id,
                    "driver_name": driver_meta["driver_name"],
                    "target_attribute": attr,
                    "matched_question": question,
                }
            if "car" in clean_q or "vehicle" in clean_q or "drive" in clean_q or "chassis" in clean_q:
                attr = f"car_for_{year}_title"
                return {
                    "driver_id": target_driver_id,
                    "driver_name": driver_meta["driver_name"],
                    "target_attribute": attr,
                    "matched_question": question,
                }

        if "how many" in clean_q or "championships count" in clean_q or "titles" in clean_q or "championship count" in clean_q:
            return {
                "driver_id": target_driver_id,
                "driver_name": driver_meta["driver_name"],
                "target_attribute": "world_drivers_championships",
                "matched_question": question,
            }

        if "which years" in clean_q or "championship years" in clean_q or "when did" in clean_q:
            return {
                "driver_id": target_driver_id,
                "driver_name": driver_meta["driver_name"],
                "target_attribute": "championship_years",
                "matched_question": question,
            }

        if "team" in clean_q or "teams" in clean_q:
            return {
                "driver_id": target_driver_id,
                "driver_name": driver_meta["driver_name"],
                "target_attribute": "championship_teams",
                "matched_question": question,
            }

        if "car" in clean_q or "cars" in clean_q:
            return {
                "driver_id": target_driver_id,
                "driver_name": driver_meta["driver_name"],
                "target_attribute": "championship_cars",
                "matched_question": question,
            }

        return None

    def query_fact(self, question: str, driver_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a real query against the active knowledge store.
        If the target attribute has been unlearned, returns truthful unavailability status.
        """
        parsed = self._match_question_attribute(question, driver_id)
        if not parsed:
            return {
                "success": False,
                "found": False,
                "driver_id": driver_id,
                "question": question,
                "error": "Question could not be resolved to any recognized F1 driver fact in the knowledge store.",
                "message": "Could not map query to driver attribute. Try selecting a suggested question.",
            }

        d_id = parsed["driver_id"]
        driver_name = parsed["driver_name"]
        attr = parsed["target_attribute"]

        working_driver = self.working_drivers.get(d_id, {})
        immutable_driver = self.immutable_drivers.get(d_id, {})
        original_value = immutable_driver.get(attr)

        is_unlearned = attr in self.unlearned_attributes.get(d_id, set()) or attr not in working_driver

        if is_unlearned:
            answer = f"The requested fact '{attr}' for {driver_name} has been purged and unlearned from the knowledge store."
            status = "UNLEARNED_UNAVAILABLE"
            found = False
        else:
            val = working_driver.get(attr)
            answer = str(val) if val is not None else "Unknown"
            status = "KNOWLEDGE_ACTIVE"
            found = True

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "QUERY_FACT",
            "driver_id": d_id,
            "attribute": attr,
            "status": status,
            "details": f"Query: '{question}' -> Status: {status} (Answer: '{answer}').",
        }
        self.audit_timeline.append(entry)

        return {
            "success": True,
            "found": found,
            "is_unlearned": is_unlearned,
            "status": status,
            "driver_id": d_id,
            "driver_name": driver_name,
            "target_attribute": attr,
            "question": question,
            "answer": answer,
            "original_value": str(original_value) if original_value is not None else None,
            "active_value": str(working_driver.get(attr)) if not is_unlearned else None,
            "source_record": {
                "driver_id": d_id,
                "driver_name": driver_name,
                "attribute": attr,
                "active_value": working_driver.get(attr),
            },
            "timestamp": entry["timestamp"],
        }

    def forget_fact(self, driver_id: str, attribute: str) -> Dict[str, Any]:
        """
        Executes an exact scoped fact forgetting operation.
        Deletes the target attribute from the working store while preserving immutable source records.
        """
        if driver_id not in self.working_drivers:
            raise KeyError(f"Driver '{driver_id}' not found in knowledge store.")

        working = self.working_drivers[driver_id]
        immutable = self.immutable_drivers[driver_id]

        if attribute not in immutable:
            raise KeyError(f"Attribute '{attribute}' does not exist on driver '{driver_id}'.")

        previous_value = working.get(attribute)

        # Remove or nullify in working dictionary
        if attribute in working:
            del working[attribute]

        self.unlearned_attributes[driver_id].add(attribute)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "FORGET_FACT",
            "driver_id": driver_id,
            "attribute": attribute,
            "status": "SUCCESS",
            "details": f"Fact '{attribute}' permanently removed from active working store for driver {immutable.get('driver_name')} ({driver_id}). Previous value: '{previous_value}'.",
        }
        self.audit_timeline.append(entry)

        return {
            "success": True,
            "action": "FORGET_FACT",
            "driver_id": driver_id,
            "driver_name": immutable.get("driver_name"),
            "attribute": attribute,
            "previous_value": str(previous_value),
            "new_value": None,
            "unlearned": True,
            "status": "SUCCESS",
            "message": f"Successfully unlearned '{attribute}' for {immutable.get('driver_name')}.",
            "timestamp": entry["timestamp"],
        }

    def verify_retention(self, driver_id: str, check_attribute: str) -> Dict[str, Any]:
        """
        Verifies that an unrelated fact remains intact after an unlearning operation.
        """
        if driver_id not in self.working_drivers:
            raise KeyError(f"Driver '{driver_id}' not found in knowledge store.")

        working = self.working_drivers[driver_id]
        immutable = self.immutable_drivers[driver_id]

        is_unlearned = check_attribute in self.unlearned_attributes.get(driver_id, set()) or check_attribute not in working
        current_value = working.get(check_attribute)
        original_value = immutable.get(check_attribute)

        retained = (not is_unlearned) and (current_value == original_value) and (current_value is not None)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "VERIFY_RETENTION",
            "driver_id": driver_id,
            "attribute": check_attribute,
            "status": "VERIFIED_RETAINED" if retained else "RETENTION_BREACH",
            "details": f"Checked retention of '{check_attribute}' for {immutable.get('driver_name')}: Retained={retained} (Value: '{current_value}').",
        }
        self.audit_timeline.append(entry)

        return {
            "success": True,
            "driver_id": driver_id,
            "driver_name": immutable.get("driver_name"),
            "attribute": check_attribute,
            "retained": retained,
            "current_value": str(current_value) if current_value is not None else None,
            "expected_value": str(original_value) if original_value is not None else None,
            "status": "RETAINED" if retained else "MISSING",
            "timestamp": entry["timestamp"],
        }

    def get_audit_timeline(self) -> List[Dict[str, Any]]:
        """Returns the audit timeline in reverse chronological order (newest first)."""
        return list(reversed(self.audit_timeline))


# Global singleton instance for the FastAPI application
f1_service = F1UnlearningService()

