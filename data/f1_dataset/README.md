# Real Formula 1 Driver Unlearning Demo Dataset

Contains public Formula 1 facts about five world champions:
Lewis Hamilton, Michael Schumacher, Max Verstappen, Sebastian Vettel, and Ayrton Senna.

Files:
- `f1_drivers.csv` and `f1_drivers.json`: driver fact records
- `f1_qa_pairs.csv` and `f1_qa_pairs.jsonl`: question-answer test cases with target attributes

## Recommended live demo
1. Load `f1_drivers.json` into the project's knowledge store.
2. Select a driver, e.g. Lewis Hamilton.
3. Ask: "Which team did Lewis Hamilton win the 2020 Drivers' Championship with?"
   Expected answer: Mercedes.
4. Request forgetting of the specific fact `team_for_2020_title` for `F1-001`.
5. Run the project's actual forgetting/deletion method, then ask the exact question again.
6. Verify that an unrelated fact, such as Hamilton's 2008 championship car, remains available.

## Important scientific distinction
If the application stores these facts in a JSON/database/retrieval index, removing a fact demonstrates record or retrieval deletion. It does not prove that a neural network's parameters have unlearned the fact. Label the operation correctly. If testing a model-unlearning algorithm, report that separately and compare actual outputs and retained-knowledge checks.

## Data notes
- Facts describe public sports achievements, teams, and cars.
- Championship years/cars are included for demonstration and should be cross-checked against official F1/FIA records before publication.
- This dataset is a small curated demo, not a complete F1 historical database.
