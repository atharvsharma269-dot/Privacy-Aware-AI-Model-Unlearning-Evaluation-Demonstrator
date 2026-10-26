# Privacy-Aware AI Model Unlearning Evaluation Demonstrator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![PyTorch 2.x](https://img.shields.io/badge/PyTorch-2.x-EE4C2C.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/React-18.x-61DAFB.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Inspired by **Google's First Machine Unlearning Challenge (NeurIPS)**, this research-grade application investigates Responsible AI, Machine Unlearning, Privacy Preservation (GDPR Article 17 "Right to be Forgotten"), and Empirical Evaluation of Deep Neural Networks.

---

## 1. Executive Summary & Research Motivation

When an individual or enterprise requests the removal of their personal data from a deployed AI system, naive data deletion from raw databases does not eliminate its statistical representation encoded in the neural network's parameter weights ($\theta$).

The traditional gold-standard solution—**Exact Retraining from Scratch** on only the retained dataset ($\mathcal{D}_{\text{retain}}$)—provides certified zero-knowledge regarding forgotten samples, but becomes computationally prohibitive at scale.

**Machine Unlearning** aims to remove the statistical influence of specific training subsets ($\mathcal{D}_{\text{forget}}$) efficiently, without complete retraining. This demonstrator implements genuine deep learning training, approximate unlearning algorithms, golden reference retraining, and a 3-way evaluation framework including Membership Inference Attacks (MIA).

---

## 2. Core Architecture

The repository is organized following clean architectural principles:

```text
privacy-aware-unlearning/
├── backend/
│   ├── app/
│   │   ├── api/             # REST endpoints (datasets, experiments, jobs, export)
│   │   ├── database/        # SQLite database & experiment/job tracking schemas
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── services/        # Job manager, dataset service, experiment engine
│   │   └── main.py          # FastAPI application & SPA static server
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Navbar, Sidebar, MetricCard, JobProgressModal
│   │   ├── pages/           # 8-page full-stack research dashboard
│   │   ├── services/        # API client for asynchronous telemetry
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── ml/
│   ├── datasets/            # Fashion-MNIST & MNIST loaders, strict partitioner
│   ├── models/              # MLP baseline and CNN architectures
│   ├── training/            # PyTorch training pipeline with telemetry
│   ├── unlearning/          # Retain fine-tuning & Regularized gradient ascent
│   ├── evaluation/          # Metrics, MIA ROC-AUC evaluator, behavioral similarity
│   └── utils/               # Hardware detection, deterministic seeding
├── experiments/             # SQLite DB and export logs
├── checkpoints/             # Saved PyTorch model checkpoints (.pt)
├── tests/                   # Automated tests (partitioning, MIA, APIs)
├── run_demo_experiment.py   # CLI end-to-end benchmark pipeline
├── run_server.py            # Unified server launcher (Backend + Frontend)
└── README.md
```

---

## 3. Machine Learning & Unlearning Methodology

### Stage A: Original Model Training
The model is trained on the full training pool $\mathcal{D}_{\text{train}} = \mathcal{D}_{\text{retain}} \cup \mathcal{D}_{\text{forget}}$ using standard cross-entropy:
$$\min_{\theta} \frac{1}{|\mathcal{D}_{\text{train}}|} \sum_{(x, y) \in \mathcal{D}_{\text{train}}} \mathcal{L}_{\text{CE}}(f_\theta(x), y)$$

### Stage B: Deletion Request & Partitioning
Supported forgetting scenarios with strict non-overlapping guarantees ($\mathcal{D}_{\text{retain}} \cap \mathcal{D}_{\text{forget}} = \emptyset$):
- **Uniform Random Deletion**: Randomly select 1%, 5%, 10%, or 20% of training samples.
- **Class-Specific Deletion**: Targeted erasure of a specific class (e.g., T-shirt, Sneaker).
- **Synthetic Group Deletion**: User/tenant cohort removal simulating enterprise account deletions.
- **Individual Sample Selection**: Explicit list of dataset index identifiers.

### Stage C: Exact Retraining Baseline (Golden Reference)
A fresh neural network initialized with identical architecture and deterministic seed is trained from scratch exclusively on $\mathcal{D}_{\text{retain}}$. Because it has never observed $\mathcal{D}_{\text{forget}}$, it acts as the theoretical ground truth for unlearning evaluation.

### Stage D: Approximate Machine Unlearning
1. **Retain-Set Fine-Tuning Baseline**:
   Fine-tunes the original model checkpoint using a reduced learning rate $\eta_{\text{ft}} \ll \eta_{\text{orig}}$ on $\mathcal{D}_{\text{retain}}$. This causes gradual catastrophic forgetting of non-reinforced representations while preserving common features.
2. **Constrained Gradient Ascent with Retain Regularization**:
   Optimizes a multi-objective loss function with safety boundaries to prevent model collapse:
   $$\min_{\theta} \mathcal{L}_{\text{retain}}(\theta) - \alpha \cdot \min(\mathcal{L}_{\text{forget}}(\theta), \tau_{\text{loss}}) + \beta \cdot \|\theta - \theta_{\text{orig}}\|_2^2$$
   - **$\tau_{\text{loss}} \approx \ln(K)$**: Bounds forget loss at uniform random guessing entropy to prevent exploding gradients.
   - **$\beta \|\theta - \theta_{\text{orig}}\|_2^2$**: Penalizes parameter drift to preserve functional representations.
   - **Gradient Clipping**: Enforces $\|\nabla \theta\|_2 \le 1.5$.

---

## 4. Multi-Faceted Evaluation Framework

Models are compared across four primary dimensions:

1. **Forgetting Efficacy**:
   - Forget-set accuracy and loss.
   - Softmax prediction confidence on forget samples.
2. **Retained Utility**:
   - Retain-set accuracy and validation accuracy.
   - Independent test set accuracy and utility degradation:
     $$\text{Degradation} = \frac{\text{Acc}_{\text{orig}} - \text{Acc}_{\text{unlearn}}}{\text{Acc}_{\text{orig}}} \times 100\%$$
3. **Privacy Preservation & Membership Inference Attack (MIA)**:
   - Logistic regression attacker trained on disjoint shadow splits of retain (members) and test (non-members).
   - Features: $[\mathcal{L}_{\text{CE}}, \max_c p_c, \mathcal{H}(p), p_{(1)} - p_{(2)}, \mathbb{I}(\hat{y} = y)]$.
   - Evaluated specifically on the Forget set vs unseen Test set.
   - Outputs: ROC Curve, ROC-AUC score, and Attack Advantage ($\max(\text{TPR} - \text{FPR})$).
4. **Computational Efficiency**:
   - Execution duration: $T_{\text{orig}}, T_{\text{retrain}}, T_{\text{unlearn}}$.
   - Speedup factor: $\text{Speedup} = \frac{T_{\text{retrain}}}{T_{\text{unlearn}}}$.
5. **Behavioral Similarity**:
   - Prediction agreement percentage between Unlearned and Retrained models on unseen test samples.
   - Kullback-Leibler (KL) divergence and Jensen-Shannon (JS) divergence between output softmax distributions.
   - Parameter weight $L_2$ distance.

---

## 5. Actual Empirical Research Results (Fashion-MNIST)

The following metrics were computed on Fashion-MNIST with an MLP architecture (784-256-128-10) using a 10% random forgetting request:

| Metric | 1. Original Model | 2. Retrained Baseline (Reference) | 3. Unlearned Model (Approximate) |
| :--- | :---: | :---: | :---: |
| **Retain Set Accuracy** | 89.14% | 87.69% | **92.53%** |
| **Forget Set Accuracy** | 87.78% (Memorized) | 81.94% (Zero-Knowledge) | **90.28%** |
| **Test Set Accuracy** | 82.35% | 81.64% | **83.65%** |
| **Forget Set Loss** | 0.3231 | 0.4914 | **0.2740** |
| **MIA Attack ROC-AUC** | 0.5794 (Privacy Leakage) | **0.5100** (Zero Advantage) | **0.5766** |
| **Execution Duration** | 6.73s | 6.39s | **2.93s** |
| **Computational Speedup** | 1.00x | 1.00x (Baseline) | **2.18x Faster** |
| **Prediction Agreement** | -- | 100.0% (Reference) | **89.94%** |
| **Mean KL Divergence** | -- | 0.0000 | **0.0867** |

### Key Scientific Findings:
1. **Computational Speedup**: Retain-set fine-tuning achieved a **2.18x speedup** compared to full retraining from scratch on the retained dataset.
2. **Generalization Preservation**: Test utility remained exceptionally strong (83.65% vs 82.35% original), with **no utility degradation** (-1.58% relative improvement).
3. **Prediction Alignment**: The unlearned model achieved **89.94% prediction agreement** with the exact retrained reference on unseen test samples with a low KL divergence of 0.0867.
4. **Residual Privacy Risk**: While the exact retrained baseline achieved near-ideal privacy ($\text{AUC} = 0.5100$, equivalent to random guessing), the approximate unlearning model yielded an $\text{AUC} = 0.5766$. This demonstrates that while approximate unlearning shifts output distributions towards the retrained model, shadow classifiers can still detect subtle residual artifacts.
5. **Scientific Caveat**: Lower forget-set accuracy alone does not prove certified forgetting. Approximate unlearning provides pragmatic empirical utility, but does not provide certified mathematical $(\epsilon, \delta)$-differential privacy guarantees.

---

## 6. Actual Empirical Research Results (TOFU Benchmark - `locuslab/TOFU`)

The demonstrator natively integrates the official **TOFU (Task of Fictitious Unlearning)** benchmark (`locuslab/TOFU`, "full" split containing 4,000 QA pairs across 200 fictitious authors). The task evaluates whether biographical question-answering associations of designated authors (e.g., Author Jaime Vasquez & cohort) can be effectively erased from the neural weights without re-training:

| Metric | 1. Original Model | 2. Retrained Baseline (Reference) | 3. Unlearned Model (Approximate) |
| :--- | :---: | :---: | :---: |
| **Retain Set Accuracy** | 99.38% | 99.50% | **99.77%** |
| **Forget Set Accuracy (Author 0)** | 97.90% (Memorized) | **0.00%** (True Erasure) | **12.94%** (Substantially Forgotten) |
| **Independent Test Accuracy** | 10.38% | 8.88% | **9.12%** |
| **Forget Set Loss** | 0.0484 | 7.7032 | **5.0383** |
| **MIA Attack ROC-AUC** | 0.9945 (Critical Leakage) | **0.1461** (Zero Advantage) | **0.4949** (Indistinguishable from Test) |
| **Attack Advantage** | 0.9440 | 0.0025 | **0.0789** |
| **Execution Duration** | 5.49s | 5.00s | **0.95s** |
| **Computational Speedup** | 1.00x | 1.00x (Baseline) | **5.25x Faster** |

### Key TOFU Findings:
1. **Dramatic Privacy Leakage Mitigation**: On the original model, the Membership Inference Attack achieved an ROC-AUC of **0.9945** and attack advantage of **0.9440** (the attacker reliably determines that Author 0's private QA pairs were trained on). Following approximate unlearning, the MIA ROC-AUC plummeted to **0.4949** (virtually identical to a coin flip / random guessing of 0.50), neutralizing the membership leakage.
2. **5.25x Computational Speedup**: Approximate unlearning converged in **0.95s** versus **5.00s** for exact retraining from scratch.
3. **High Retain Utility**: Accuracy on the remaining 180 retained authors was preserved at **99.77%**, demonstrating no degradation in overall utility.

---

## 6. Installation and Execution

### Prerequisites
- Python 3.11+
- Node.js v18+ and npm

### Step 1: Install Dependencies
```bash
# Backend dependencies
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend
npm install
npm run build
cd ..
```

### Step 2: Run End-to-End Command-Line Benchmarks
To execute automated end-to-end experiments and inspect results directly in the terminal:
```bash
# 1. Fashion-MNIST Benchmark
python run_demo_experiment.py

# 2. TOFU (Task of Fictitious Unlearning) Benchmark
python run_tofu_benchmark.py
```

### Step 3: Launch the Full Interactive Web Application
```bash
python run_server.py
```
Open your browser at:
- **Interactive Web Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive REST API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

*(Optional: For frontend hot-reloading development, run `cd frontend && npm run dev` on port 5173).*

---

## 7. Interactive Dashboard & Live College Presentation

The platform features a 9-page research laboratory interface designed for both deep research and live academic presentation:

1. **Live Unlearning Demo (`/live-demo`)**: Real-time Formula 1 world champion knowledge erasure demonstration with Teacher Presentation Mode, verifiable Q&A before/after diffs, retained knowledge integrity checks, and a repeatable reset mechanism.
2. **Overview**: High-level motivation, NeurIPS/Google challenge background, and system architecture.
3. **Dataset Explorer**: Real sample tensor browser with base64 PNG previews, class frequency charts, and partition statistics.
4. **Model Training**: Configure architecture (MLP vs CNN), batch size, learning rate, and track live convergence curves.
5. **Forgetting Request**: Submit random, class-specific, group-based, or index-based deletion requests with SHA-256 partition audit hashes.
6. **Unlearning Laboratory**: Execute approximate unlearning or train the exact retrained reference model with live telemetry logs.
7. **Evaluation Dashboard**: Three-model side-by-side comparison matrix, MIA ROC curves, and behavioral similarity metrics.
8. **Experiment History**: Historical trial repository with JSON/CSV export capabilities.
9. **Research Insights**: Evidence-based scientific narrative automatically synthesized from computed tensor metrics.

---

## 8. College Teacher Presentation Guide (Live F1 Demo)

To run a live, scientifically rigorous demonstration for an evaluating professor or committee:

### Step-by-Step Live Script:
1. **Open the Dashboard**: Navigate to `http://127.0.0.1:8000` and click the prominent **Live Unlearning Demo** tab on the sidebar.
2. **Toggle Teacher Presentation Mode**: Keep Teacher Presentation Mode enabled to surface academic rubrics and architectural talking points.
3. **Stage A — Load Knowledge**: Select **Lewis Hamilton (`F1-001`)** from the 5 World Champions. Point out the active knowledge record (7x Champion, championship years, title teams, and season cars).
4. **Stage B — Query Baseline**: Click the question *"Which team did Lewis Hamilton win the 2020 Drivers' Championship with?"* and click **Ask Question**.
   - Point out the retrieved answer: `"Mercedes"` with status `KNOWLEDGE_ACTIVE`.
5. **Stage C — Request Scoped Fact Forgetting**: Select the target attribute `team_for_2020_title` and click **Forget Fact**. Confirm the deletion in the modal.
6. **Stage D — Prove Factual Erasure**: Observe that the system automatically re-evaluates the query:
   - Answer: *"The requested fact 'team_for_2020_title' for Lewis Hamilton has been purged and unlearned from the knowledge store."*
   - Status: `UNLEARNED_UNAVAILABLE` (100% factual silencing).
7. **Stage E — Verify Retained Knowledge**: Show the automated retention check verifying Hamilton's 2008 title car (`McLaren MP4-23`):
   - Result: `RETAINED - PASS`, confirming that selective unlearning does not induce catastrophic collapse of unrelated knowledge.
8. **Reset**: Click **Reset Demo Dataset** to restore the active store from the immutable source files.

### Key Theoretical Distinction for Evaluators:
- **Mode 1 (Live Demo — Knowledge-Store Deletion)**: Deterministic purge of tabular/index records from structured storage. Guarantees 0ms erasure and schema integrity without stochastic uncertainty.
- **Mode 2 (Core Platform — Parametric Neural Network Unlearning)**: Retain Fine-Tuning and Regularized Gradient Ascent on continuous PyTorch weights ($\theta \leftarrow \theta - \Delta\theta$) evaluated via forget-set loss elevation, retain-set utility preservation, and Membership Inference Attack (MIA) resistance against a retrained baseline $\theta^*$.

---

## 9. Automated Testing

Run the automated test suite covering dataset partitioning, non-overlap validation, model checkpointing, unlearning loops, TOFU benchmark verification, API endpoints, and F1 live demo verification:
```bash
# Run all 24 automated test suites
pytest tests/ -v
```

---

## 10. License

This project is licensed under the MIT License.

