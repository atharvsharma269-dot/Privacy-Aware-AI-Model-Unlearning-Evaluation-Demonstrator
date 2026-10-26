import csv
import io
import json
from fastapi import APIRouter, HTTPException, Query, Response
from ..services.experiment_service import ExperimentService

router = APIRouter(prefix="/api/experiments", tags=["export"])
exp_service = ExperimentService()


@router.get("/{experiment_id}/export")
def export_experiment(experiment_id: str, format: str = Query("json", description="'json' or 'csv'")):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if format.lower() == "csv":
        m = exp.get("metrics") or {}
        orig = m.get("original_model") or {}
        unl = m.get("unlearned_model") or {}
        ret = m.get("retrained_model") or {}
        mia = m.get("mia") or {}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Experiment ID", exp["id"]])
        writer.writerow(["Name", exp["name"]])
        writer.writerow(["Dataset", exp["dataset_name"]])
        writer.writerow(["Model Architecture", exp["model_name"]])
        writer.writerow(["Random Seed", exp["seed"]])
        writer.writerow(["Created At", exp["created_at"]])
        writer.writerow([])
        writer.writerow(["Metric", "Original Model", "Retrained Reference", "Unlearned Model"])

        def get_val(d, *keys):
            curr = d
            for k in keys:
                if not isinstance(curr, dict) or k not in curr:
                    return "N/A"
                curr = curr[k]
            return curr

        writer.writerow(["Retain Set Accuracy (%)", get_val(orig, "retain", "accuracy"), get_val(ret, "retain", "accuracy"), get_val(unl, "retain", "accuracy")])
        writer.writerow(["Forget Set Accuracy (%)", get_val(orig, "forget", "accuracy"), get_val(ret, "forget", "accuracy"), get_val(unl, "forget", "accuracy")])
        writer.writerow(["Validation Accuracy (%)", get_val(orig, "val", "accuracy"), get_val(ret, "val", "accuracy"), get_val(unl, "val", "accuracy")])
        writer.writerow(["Test Accuracy (%)", get_val(orig, "test", "accuracy"), get_val(ret, "test", "accuracy"), get_val(unl, "test", "accuracy")])
        writer.writerow(["Retain Loss", get_val(orig, "retain", "loss"), get_val(ret, "retain", "loss"), get_val(unl, "retain", "loss")])
        writer.writerow(["Forget Loss", get_val(orig, "forget", "loss"), get_val(ret, "forget", "loss"), get_val(unl, "forget", "loss")])
        writer.writerow(["Execution Time (s)", get_val(orig, "training_time_seconds"), get_val(ret, "retraining_time_seconds"), get_val(unl, "unlearning_time_seconds")])
        writer.writerow(["MIA Forget Set ROC-AUC", get_val(mia, "original", "roc_auc"), get_val(mia, "retrained", "roc_auc"), get_val(mia, "unlearned", "roc_auc")])
        writer.writerow(["Computational Speedup Factor", "1.0x (Reference)", "1.0x (Baseline)", f"{m.get('speedup_factor', 'N/A')}x"])
        writer.writerow(["Utility Degradation (%)", "0.0%", "N/A", f"{unl.get('utility_degradation_pct', 'N/A')}%"])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}.csv"},
        )

    # Default JSON
    return Response(
        content=json.dumps(exp, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}.json"},
    )

