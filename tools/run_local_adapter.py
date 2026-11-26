"""Run the fine-tuned ClaimBack adapter locally (e.g. on a free Google Colab GPU) and save its answers.

1. Download the adapter from Adaption (AutoScientist tab, or with the Adaption Python SDK:
   client.autoscientist.download(run_id).write_to_file("adapter.tar.gz")), then:  tar -xzf adapter.tar.gz -d adapter
2. pip install "transformers>=4.51" peft accelerate torch
3. python tools/run_local_adapter.py adapter/ test_clean.jsonl predictions.jsonl
4. python tools/eval_extraction.py test_clean.jsonl predictions.jsonl

The base model is Qwen/Qwen3.5-4B, downloaded from Hugging Face on first run (about 8 GB).
Letters are sent exactly as in training: one user message, no system prompt, greedy decoding.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_model import IN_KEYS, parse_answer  # noqa: E402

BASE = "Qwen/Qwen3.5-4B"


def find_adapter(path: Path) -> Path:
    """The tarball may nest the adapter one level down; find the folder holding adapter_config.json."""
    hits = list(path.rglob("adapter_config.json"))
    if not hits:
        sys.exit(f"No adapter_config.json under {path}")
    return hits[0].parent


def main(adapter_dir, test_path, out_path):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter = find_adapter(Path(adapter_dir))
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None)
    model = PeftModel.from_pretrained(model, str(adapter)).eval()

    rows = [json.loads(l) for l in open(test_path, encoding="utf-8")]
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            letter = next(r[k] for k in IN_KEYS if k in r)
            msgs = [{"role": "user", "content": letter}]
            try:  # Qwen chat templates can add a "thinking" block; turn it off where supported.
                prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            except TypeError:
                prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = tok(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=400, do_sample=False)
            text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
            f.write(json.dumps(parse_answer(text), ensure_ascii=False) + "\n")
            print(f"\r{i}/{len(rows)}", end="", flush=True)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
