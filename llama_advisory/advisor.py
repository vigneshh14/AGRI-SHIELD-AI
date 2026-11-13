#!/usr/bin/env python3
"""
M5 - the Llama advisory layer.

Design
------
Two independent safety mechanisms, because one is not enough:

  INPUT SIDE  (knowledge_base/retrieval.py)
      In abstain mode, chemical fields are never copied into the prompt. The
      model cannot repeat what it was never given.

  OUTPUT SIDE (this file, `guard_output`)
      Generated text is scanned for pesticide actives and dose patterns. If an
      abstain-mode response contains either, the response is REPLACED with a
      safe fallback and the violation is recorded. This catches a model that
      hallucinates a chemical from its pretraining rather than from the prompt.

Backends
--------
    MockBackend          deterministic, offline, for pipeline tests. Every
                         response it produces is stamped backend="mock".
    ExecuTorchBackend    the real thing. Raises until a .pte and tokenizer
                         exist. Running it successfully on Arm is a SEPARATE
                         acceptance criterion and is not satisfied by any mock.

Run the tests:
    python advisor.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "knowledge_base"))

PROMPTS = Path(__file__).resolve().parent / "prompts"


# --------------------------------------------------------------------------
# structured schemas
# --------------------------------------------------------------------------
@dataclass
class AdvisoryRequest:
    class_label: str
    confidence: float
    severity: str = "unknown"
    lang: str = "en"
    threshold: float = 0.70


@dataclass
class AdvisoryResponse:
    text: str
    advisory_mode: str                 # "prescriptive" | "abstain"
    reason: str
    lang: str
    backend: str                       # "mock" | "executorch"
    is_mock: bool
    record_id: str | None = None
    confidence: float | None = None
    guard: dict = field(default_factory=dict)
    acceptance: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# output guard
# --------------------------------------------------------------------------
# Common actives used on tomato in Indian advisories. This is a BLOCKLIST used
# to suppress output, never to generate it.
CHEMICAL_TERMS = [
    "mancozeb", "chlorothalonil", "copper oxychloride", "copper hydroxide",
    "metalaxyl", "cymoxanil", "azoxystrobin", "difenoconazole", "carbendazim",
    "propineb", "captan", "thiophanate", "fosetyl", "dimethomorph",
    "famoxadone", "tebuconazole", "hexaconazole", "zineb", "ziram",
    "bordeaux mixture", "imidacloprid", "thiamethoxam", "spinosad",
    "chlorantraniliprole", "emamectin", "fungicide", "pesticide", "insecticide",
]
DOSE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:g|gm|gram|kg|ml|l|litre|liter|%)\s*(?:/|per\b)\s*"
    r"(?:l\b|litre|liter|ha\b|hectare|acre|plant|tree)",
    re.IGNORECASE,
)
SPRAY_RE = re.compile(r"\bspray\s+\w+\s+(?:at|@)\s*\d", re.IGNORECASE)

SAFE_FALLBACK = {
    "en": ("I am not confident enough to recommend a treatment for this leaf. "
           "Please show it to your local agricultural extension officer before "
           "applying anything."),
    "ta": ("இந்த இலைக்கு சிகிச்சை பரிந்துரைக்க போதுமான உறுதி இல்லை. "
           "எதையும் பயன்படுத்தும் முன் உங்கள் உள்ளூர் வேளாண் அலுவலரிடம் காட்டுங்கள்."),
}


def guard_output(text: str, advisory_mode: str, allowed_chemicals: list | None = None) -> dict:
    """Scan generated text. Returns a verdict dict; does not mutate text."""
    low = text.lower()
    allowed = {c.lower() for c in (allowed_chemicals or [])}
    found = [t for t in CHEMICAL_TERMS if t in low and t not in allowed]
    doses = DOSE_RE.findall(text)
    sprays = SPRAY_RE.findall(text)

    if advisory_mode == "abstain":
        violated = bool(found or doses or sprays)
    else:
        # in prescriptive mode only chemicals absent from the record are a problem
        violated = bool(found)

    return {"violated": violated, "chemical_terms": found,
            "dose_patterns": doses, "spray_patterns": sprays,
            "scanned_chars": len(text)}


# --------------------------------------------------------------------------
# prompts
# --------------------------------------------------------------------------
def build_prompt(packet: dict) -> str:
    ctx = packet["prompt_context"]
    lang = ctx.get("language", "en")
    tpl = (PROMPTS / f"advisory_{lang}.txt").read_text(encoding="utf-8")

    def bullets(items):
        return "\n".join(f"- {i}" for i in items) if items else "- (none given)"

    chem = ctx.get("chemical_interventions")
    chem_block = (json.dumps(chem, ensure_ascii=False, indent=2)
                  if chem else "(NONE PROVIDED - you must not name any)")

    return tpl.format(
        crop=ctx.get("crop", "unknown"),
        disease=ctx.get("disease", "unknown"),
        confidence=ctx.get("confidence", 0.0),
        severity=ctx.get("severity", "unknown"),
        symptoms=bullets(ctx.get("symptoms", [])),
        practices=bullets(ctx.get("cultural_practices", [])),
        chemicals=chem_block,
        instruction=ctx.get("instruction", ""),
    )


# --------------------------------------------------------------------------
# backends
# --------------------------------------------------------------------------
class LlamaBackend(Protocol):
    name: str
    is_mock: bool

    def generate(self, prompt: str, max_tokens: int = 220) -> str: ...


class MockBackend:
    """Deterministic stand-in. Produces NO chemical content, ever."""
    name = "mock"
    is_mock = True

    def generate(self, prompt: str, max_tokens: int = 220) -> str:
        crop = re.search(r"Crop:\s*(.+)", prompt)
        dis = re.search(r"Condition:\s*(.+)", prompt)
        sev = re.search(r"Severity:\s*(.+)", prompt)
        conf = re.search(r"Confidence:\s*([\d.]+)", prompt)
        ta = "தமிழ்" in prompt or "இலை" in prompt
        c = crop.group(1).strip() if crop else "crop"
        d = dis.group(1).strip() if dis else "condition"
        s = sev.group(1).strip() if sev else "unknown"
        p = conf.group(1) if conf else "?"
        if ta:
            return (f"[MOCK] {c} பயிரில் {d} இருக்கலாம் (நம்பிக்கை {p}, தீவிரம் {s}). "
                    f"பாதித்த இலைகளை அகற்றவும், இலைகள் உலர இடைவெளி விடவும். "
                    f"மருந்து பயன்படுத்தும் முன் வேளாண் அலுவலரிடம் உறுதி செய்யவும்.")
        return (f"[MOCK] This {c} leaf most likely shows {d} "
                f"(confidence {p}, severity {s}). Remove and destroy affected leaves, "
                f"keep the foliage dry, and confirm with your local agricultural "
                f"extension officer before applying anything.")


class ExecuTorchBackend:
    """
    Real Llama 3.2 1B through the ExecuTorch runtime.

    ACCEPTANCE CRITERION, separate from every mock test:
        this backend generates coherent text from a .pte on the Arm device,
        offline, with the output captured.
    Until that happens, M3 and M4 are UNSATISFIED. No mock run changes that.
    """
    name = "executorch"
    is_mock = False

    def __init__(self, pte: Path, tokenizer: Path, runner: Path | None = None):
        self.pte, self.tokenizer, self.runner = Path(pte), Path(tokenizer), runner
        missing = [str(p) for p in (self.pte, self.tokenizer) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                "ExecuTorch Llama backend unavailable; missing: " + ", ".join(missing) +
                ". This is expected until the Llama licence is approved and the model "
                "is exported. Do NOT substitute a mock and report it as satisfied.")

    def generate(self, prompt: str, max_tokens: int = 220) -> str:
        raise NotImplementedError(
            "Wire this to the ExecuTorch llama runner once the .pte exists. "
            "On device this shells out to llama_main over adb; on desktop it uses "
            "executorch.extension.llm. Leaving it unimplemented is deliberate: a "
            "silent fallback to a mock here would be exactly the kind of unearned "
            "claim the project rules forbid.")


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------
def advise(kb, req: AdvisoryRequest, backend: LlamaBackend) -> AdvisoryResponse:
    from retrieval import retrieve
    packet = retrieve(kb, req.class_label, req.confidence,
                      severity=req.severity, lang=req.lang, threshold=req.threshold)
    prompt = build_prompt(packet)
    raw = backend.generate(prompt)

    allowed = [c.get("name", "") for c in
               packet["prompt_context"].get("chemical_interventions", [])]
    verdict = guard_output(raw, packet["advisory_mode"], allowed)

    text = raw
    if verdict["violated"]:
        text = SAFE_FALLBACK.get(req.lang, SAFE_FALLBACK["en"])

    return AdvisoryResponse(
        text=text,
        advisory_mode=packet["advisory_mode"],
        reason=packet["reason"],
        lang=req.lang,
        backend=backend.name,
        is_mock=backend.is_mock,
        record_id=packet.get("record_id"),
        confidence=req.confidence,
        guard=verdict,
        acceptance={
            "mandatory_M3_executorch_runtime": not backend.is_mock,
            "note": ("MOCK OUTPUT - does not satisfy M3/M4. Real Llama inference "
                     "on Arm is a separate acceptance criterion."
                     if backend.is_mock else
                     "Real ExecuTorch backend used."),
        },
    )


# --------------------------------------------------------------------------
def self_test() -> int:
    from retrieval import KnowledgeBase, DEFAULT_KB
    kb = KnowledgeBase(DEFAULT_KB)
    mock = MockBackend()
    fails = []

    print("=== mock advisory, both languages ===")
    for lang in ("en", "ta"):
        r = advise(kb, AdvisoryRequest("Tomato___Late_blight", 0.95, "severe", lang), mock)
        print(f"  [{lang}] mode={r.advisory_mode} mock={r.is_mock} "
              f"guard_violated={r.guard['violated']}")
        print(f"       {r.text[:110]}...")
        if r.guard["violated"]:
            fails.append(f"mock produced blocked content in {lang}")
        if not r.is_mock:
            fails.append("mock not flagged as mock")

    print("\n=== output guard catches a hallucinated chemical ===")
    bad_en = "Spray mancozeb 2 g/L every 7 days to control the blight."
    v = guard_output(bad_en, "abstain")
    ok = v["violated"] and "mancozeb" in v["chemical_terms"] and v["dose_patterns"]
    print(f"  [{'PASS' if ok else 'FAIL'}] blocked: terms={v['chemical_terms']} "
          f"doses={v['dose_patterns']}")
    if not ok:
        fails.append("guard missed a chemical + dose")

    bad_dose_only = "Apply 3 ml/L of the solution to each plant."
    v2 = guard_output(bad_dose_only, "abstain")
    print(f"  [{'PASS' if v2['violated'] else 'FAIL'}] dose-only text blocked: "
          f"{v2['dose_patterns']}")
    if not v2["violated"]:
        fails.append("guard missed a bare dose")

    clean = "Remove affected leaves and keep the foliage dry. Consult your extension officer."
    v3 = guard_output(clean, "abstain")
    print(f"  [{'PASS' if not v3['violated'] else 'FAIL'}] clean advice allowed through")
    if v3["violated"]:
        fails.append("guard false-positived on clean advice")

    print("\n=== a violating generation is REPLACED, not just flagged ===")
    class Rogue:
        name, is_mock = "rogue-mock", True
        def generate(self, prompt, max_tokens=220):
            return "Spray chlorothalonil 2 g/L immediately."
    r = advise(kb, AdvisoryRequest("Tomato___Early_blight", 0.99), Rogue())
    replaced = "chlorothalonil" not in r.text.lower() and r.guard["violated"]
    print(f"  [{'PASS' if replaced else 'FAIL'}] text replaced with safe fallback")
    print(f"       {r.text[:100]}")
    if not replaced:
        fails.append("violating text was not replaced")

    print("\n=== ExecuTorch backend refuses to pretend ===")
    try:
        ExecuTorchBackend(Path("does_not_exist.pte"), Path("nope.model"))
        fails.append("ExecuTorchBackend constructed without artifacts")
        print("  [FAIL] constructed anyway")
    except FileNotFoundError as e:
        print(f"  [PASS] refused: {str(e)[:95]}...")

    print()
    if fails:
        print(f"FAILED: {fails}")
        return 1
    print("ALL PASS")
    print("\nREMINDER: every response above came from a MOCK. M3 and M4 remain "
          "unsatisfied until real Llama inference runs on the Arm device.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--class-label")
    ap.add_argument("--confidence", type=float, default=0.9)
    ap.add_argument("--lang", default="en", choices=["en", "ta"])
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if a.class_label:
        from retrieval import KnowledgeBase, DEFAULT_KB
        print(advise(KnowledgeBase(DEFAULT_KB),
                     AdvisoryRequest(a.class_label, a.confidence, lang=a.lang),
                     MockBackend()).to_json())
    else:
        ap.print_help()
