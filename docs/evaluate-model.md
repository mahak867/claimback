# Evaluating the fine-tuned ClaimBack model

Run 1 ([training-run-1.json](training-run-1.json)): Qwen/Qwen3.5-4B, LoRA, 2 epochs, trained on dataset v2 with Adaption AutoScientist. It is tested on the 401 usable v1 letters, which it never saw.

## Steps

1. Build the test set (once):

   ```bash
   python tools/validate_dataset.py indian_health_rejections_v1.csv
   ```

   This writes `indian_health_rejections_v1_clean.jsonl`.

2. Point the runner at the deployed model. Any OpenAI-compatible endpoint works (Adaption's API, Together AI, or the exported weights served locally with Ollama or vLLM). Set these in your own terminal; never commit a key:

   ```bash
   export CLAIMBACK_BASE_URL="https://<endpoint>/v1"
   export CLAIMBACK_MODEL="<deployed model name>"
   export CLAIMBACK_API_KEY="<key>"
   ```

3. Run the model on the 401 letters and score it:

   ```bash
   python tools/run_model.py indian_health_rejections_v1_clean.jsonl run1_predictions.jsonl
   python tools/eval_extraction.py indian_health_rejections_v1_clean.jsonl run1_predictions.jsonl
   ```

4. For the same letters, the baselines to beat:

   ```bash
   python tools/eval_extraction.py indian_health_rejections_v1_clean.jsonl
   ```

## Targets (on the 401 held-out v1 letters)

| Measure | Rules baseline | Simple classifier trained on v2 | Target for the model |
| --- | --- | --- | --- |
| Rejection reason | 79.6% accuracy | 0.805 macro-F1 | above both |
| Exact reason sentence | 7.7% | n/a | above 90% |
| Quotes found word for word | 99.5% (of what rules pick) | n/a | 100% shown to users (unverified ones are blocked anyway) |
| Mean of 11 fields | 64.5% | n/a | above 85% |

Record the results in [results.md](results.md), with a screenshot of the training curve from Adaption.
