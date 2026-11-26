"""Run the fine-tuned ClaimBack adapter locally (e.g. on a free Google Colab GPU) and save its answers.

1. Download the adapter from Adaption (AutoScientist tab, or with the Adaption Python SDK:
   client.autoscientist.download(run_id).write_to_file("adapter.tar.gz")), then:  tar -xzf adapter.tar.gz -d adapter
2. pip install "transformers>=5.13" peft accelerate torch   (Qwen3.5 needs transformers 5.13+)
3. python tools/run_local_adapter.py adapter/ test_clean.jsonl predictions.jsonl
4. python tools/eval_extraction.py test_clean.jsonl predictions.jsonl

The base model is Qwen/Qwen3.5-4B, downloaded from Hugging Face on first run (about 8 GB).
Letters are sent exactly as in training: one user message, no system prompt, greedy decoding.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_model import IN_KEYS, SYSTEM, parse_answer  # noqa: E402

BASE = os.environ.get("CLAIMBACK_BASE", "Qwen/Qwen3.5-4B")


def find_adapter(path: Path) -> Path:
    """The tarball may nest the adapter one level down; find the folder holding adapter_config.json."""
    hits = list(path.rglob("adapter_config.json"))
    if not hits:
        sys.exit(f"No adapter_config.json under {path}")
    return hits[0].parent


def text_only_adapter(adapter: Path) -> Path:
    """Adaption trains on Qwen3.5's multimodal class, whose language layers are named
    `model.language_model.layers.*`. The text-only class names them `model.layers.*`, and PEFT would
    then silently leave the LoRA weights empty. Write a copy with the names mapped."""
    from safetensors.torch import load_file, save_file

    weights = load_file(str(adapter / "adapter_model.safetensors"))
    if not any(".language_model." in k for k in weights):
        return adapter
    out = adapter.parent / (adapter.name + "_text")
    out.mkdir(exist_ok=True)
    for f in adapter.iterdir():
        if f.name != "adapter_model.safetensors" and f.is_file():
            (out / f.name).write_bytes(f.read_bytes())
    save_file({k.replace(".language_model.", "."): v for k, v in weights.items()}, str(out / "adapter_model.safetensors"))
    return out


def main(adapter_dir, test_path, out_path):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter = find_adapter(Path(adapter_dir))
    # Use the tokenizer and chat template saved with the adapter: exactly what training used.
    tok = AutoTokenizer.from_pretrained(str(adapter) if (adapter / "tokenizer_config.json").exists() else BASE)
    # bfloat16 is the training precision and halves memory (~9 GB), so it also fits CPU-only machines.
    model = AutoModelForCausalLM.from_pretrained(
        BASE, dtype=torch.bfloat16, low_cpu_mem_usage=True,
        device_map="auto" if torch.cuda.is_available() else None)
    # CLAIMBACK_NO_ADAPTER=1 runs the untuned base model, for a like-for-like comparison.
    if os.environ.get("CLAIMBACK_NO_ADAPTER") != "1":
        model = PeftModel.from_pretrained(model, str(text_only_adapter(adapter)))
    model = model.eval()

    rows = [json.loads(l) for l in open(test_path, encoding="utf-8")]
    limit = int(os.environ.get("CLAIMBACK_LIMIT", "0"))
    rows = rows[:limit] if limit else rows
    start = time.time()
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            letter = next(r[k] for k in IN_KEYS if k in r)
            msgs = [{"role": "user", "content": letter}]
            if os.environ.get("CLAIMBACK_SYSTEM_PROMPT") == "1":  # state the 11-field schema explicitly
                msgs.insert(0, {"role": "system", "content": SYSTEM})
            try:  # Qwen chat templates can add a "thinking" block; turn it off where supported.
                prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            except TypeError:
                prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = tok(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=400, do_sample=False)
            text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
            f.write(json.dumps(parse_answer(text), ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i}/{len(rows)}  {(time.time() - start) / i:.1f}s per letter", flush=True)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
