# Expert review workflow

Generate the structured expert-review package with:

```bash
python tools/prepare_expert_review_package_v1_11.py
```

Aggregate completed reviews with:

```bash
python tools/aggregate_expert_reviews_v1_11.py --input-dir outputs/expert_review_v1.11/completed_reviews --outdir outputs/expert_review_v1.11/aggregation
```
