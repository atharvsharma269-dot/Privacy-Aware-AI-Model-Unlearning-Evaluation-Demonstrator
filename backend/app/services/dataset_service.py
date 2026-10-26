import base64
import io
from typing import Dict, List, Optional, Any
import numpy as np
from PIL import Image
from ml.datasets.loader import load_raw_dataset, get_dataset_class_names


class DatasetService:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self._cache: Dict[str, Any] = {}

    def get_raw_datasets(self, dataset_name: str = "fashion_mnist"):
        key = dataset_name.lower().strip()
        if key not in self._cache:
            train_ds, test_ds, classes = load_raw_dataset(key, data_dir=self.data_dir, download=True)
            self._cache[key] = {
                "train": train_ds,
                "test": test_ds,
                "classes": classes,
            }
        return self._cache[key]["train"], self._cache[key]["test"], self._cache[key]["classes"]

    def get_summary(self, dataset_name: str = "fashion_mnist") -> Dict[str, Any]:
        train_ds, test_ds, classes = self.get_raw_datasets(dataset_name)
        total_train = len(train_ds)
        total_test = len(test_ds)

        # Count train class distribution
        class_counts = {c: 0 for c in classes}
        # Sample or iterate
        for i in range(min(total_train, 60000)):
            _, _, target = train_ds[i]
            class_counts[classes[int(target)]] += 1

        return {
            "name": dataset_name,
            "total_train": total_train,
            "total_test": total_test,
            "num_classes": len(classes),
            "classes": classes,
            "class_distribution_train": class_counts,
        }

    def get_samples(
        self,
        dataset_name: str = "fashion_mnist",
        split: str = "train",
        offset: int = 0,
        limit: int = 24,
        class_filter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if "tofu" in dataset_name.lower():
            from ml.datasets.tofu_loader import get_tofu_raw_sample
            train_ds, test_ds, classes = self.get_raw_datasets(dataset_name)
            ds = train_ds if split == "train" else test_ds
            samples: List[Dict[str, Any]] = []
            collected = 0
            idx = offset
            while collected < limit and idx < len(ds):
                sample_data = get_tofu_raw_sample(idx, split=split)
                idx += 1
                if class_filter is not None and sample_data["cohort_class"] != class_filter:
                    continue
                samples.append({
                    "index": sample_data["index"],
                    "label": sample_data["cohort_class"],
                    "class_name": sample_data["class_name"],
                    "image_base64": sample_data["image_base64"],
                    "question": sample_data["question"],
                    "answer": sample_data["answer"],
                    "author_id": sample_data["author_id"],
                })
                collected += 1
            return samples

        train_ds, test_ds, classes = self.get_raw_datasets(dataset_name)
        ds = train_ds if split == "train" else test_ds

        samples: List[Dict[str, Any]] = []
        collected = 0
        idx = offset

        while collected < limit and idx < len(ds):
            raw_idx, img_tensor, target = ds[idx]
            target_int = int(target)
            idx += 1

            if class_filter is not None and target_int != class_filter:
                continue

            # Convert 1x28x28 normalized tensor back to PIL Image
            # Undo normalization: approx (img * 0.35 + 0.28) * 255
            img_np = img_tensor.squeeze().cpu().numpy()
            img_min, img_max = img_np.min(), img_np.max()
            if img_max > img_min:
                img_np = (img_np - img_min) / (img_max - img_min) * 255.0
            else:
                img_np = img_np * 255.0
            img_np = np.clip(img_np, 0, 255).astype(np.uint8)

            pil_img = Image.fromarray(img_np, mode="L")
            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

            samples.append({
                "index": int(raw_idx),
                "label": target_int,
                "class_name": classes[target_int],
                "image_base64": img_b64,
            })
            collected += 1

        return samples

