# Evaluating the fine-tuned ClaimBack model

Run 1 ([training-run-1.json](training-run-1.json)): Qwen/Qwen3.5-4B + a LoRA adapter (rank 16, 1 epoch) trained on dataset v2 with Adaption AutoScientist. It is tested on the **401 usable v1 letters it never saw**: [`eval/test_v1_held_out.jsonl`](../eval/test_v1_held_out.jsonl).

## Option A: free Google Colab GPU (recommended, about 20 minutes)

1. Open [colab.research.google.com](https://colab.research.google.com), New notebook, then Runtime > Change runtime type > **T4 GPU**.
2. Download the adapter from Adaption (AutoScientist tab), or in a Colab cell with your key (never commit it or paste it in chat):

   ```python
   from getpass import getpass
   !pip -q install adaption
   from adaption import Adaption
   client = Adaption(api_key=getpass("Adaption API key: "))
   client.autoscientist.download("<run id from the AutoScientist tab>").write_to_file("adapter.tar.gz")
   ```

3. Run these cells:

   ```python
   !git clone https://github.com/mahak867/claimback && mkdir -p adapter && tar -xzf adapter.tar.gz -C adapter
   !pip -q install "transformers>=4.51" peft accelerate
   %cd claimback
   !python tools/run_local_adapter.py ../adapter eval/test_v1_held_out.jsonl run1_predictions.jsonl
   !python tools/eval_extraction.py eval/test_v1_held_out.jsonl run1_predictions.jsonl
   !python tools/eval_extraction.py eval/test_v1_held_out.jsonl
   ```

   The last line prints the rule-based baseline on the same letters for comparison.

4. Copy the two printed tables here (or into the chat) and download `run1_predictions.jsonl`.

## Option B: a hosted endpoint

If Adaption (or Together AI, vLLM, Ollama) serves the model behind an OpenAI-compatible URL:

```bash
export CLAIMBACK_BASE_URL="https://<endpoint>/v1"
export CLAIMBACK_MODEL="<deployed model name>"
export CLAIMBACK_API_KEY="<key>"
python tools/run_model.py eval/test_v1_held_out.jsonl run1_predictions.jsonl
python tools/eval_extraction.py eval/test_v1_held_out.jsonl run1_predictions.jsonl
```

Both options ask the model exactly as it was trained: the letter as a single user message, no system prompt, greedy decoding.

## Targets (on the 401 held-out v1 letters)

| Measure | Rules baseline | Simple classifier trained on v2 | Target for the model |
| --- | --- | --- | --- |
| Rejection reason | 79.6% accuracy | 0.805 macro-F1 | above both |
| Exact reason sentence | 7.7% | n/a | above 90% |
| Mean of 11 fields | 64.5% | n/a | above 85% |

Record the results in [results.md](results.md).
