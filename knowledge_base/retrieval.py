#!/usr/bin/env python3
"""
M6 - offline knowledge retrieval, and the gate that decides what Llama may say.

The safety property this module exists to guarantee
---------------------------------------------------
    A chemical name, dose or interval can only appear in the model's prompt
    when BOTH of these hold:
      (a) the classifier's confidence is at or above the threshold, AND
      (b) the matching knowledge-base record is marked sourced=true AND
          actually carries verified chemical_interventions.

This is enforced structurally: in abstain mode the chemical fields are never
copied into the prompt dictionary at all. The model cannot repeat what it was
never given. Asking it nicely not to prescribe is not a control; withholding
the text is.

Run the self-test:
    python retrieval.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_KB = Path(__file__).resolve().parent / "diseases.json"
DEFAULT_THRESHOLD = 0.70


class KnowledgeBase:
    def __init__(self, path: Path = DEFAULT_KB):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.records = {r["class_label"]: r for r in data["records"]}
        self.meta = {k: v for k, v in data.items() if k != "records"}

    def get(self, class_label: str) -> dict | None:
        return self.records.get(class_label)

    def coverage(self) -> dict:
        total = len(self.records)
        sourced = sum(1 for r in self.records.values() if r["sourced"])
        with_chem = sum(1 for r in self.records.values() if r["chemical_interventions"])
        return {"records": total, "sourced": sourced, "with_verified_chemicals": with_chem}


def retrieve(kb: KnowledgeBase, class_label: str, confidence: float,
             severity: str = "unknown", lang: str = "en",
             threshold: float = DEFAULT_THRESHOLD) -> dict:
    """
    Build the advisory packet handed to the Llama layer.

    Returns a dict whose 'prompt_context' is the ONLY thing the model sees.
    """
    record = kb.get(class_label)

    if record is None:
        return {
            "advisory_mode": "abstain",
            "reason": "no_knowledge_base_record",
            "confidence": confidence,
            "prompt_context": {
                "situation": "The crop condition could not be matched to a known record.",
                "instruction": "Tell the farmer the system cannot identify this and "
                               "advise consulting the local agricultural extension officer. "
                               "Name no chemical, dose or product.",
                "language": lang,
            },
        }

    confident = confidence >= threshold
    verified_chemicals = bool(record["sourced"] and record["chemical_interventions"])
    prescriptive = confident and verified_chemicals

    sym = record["symptoms_ta" if lang == "ta" else "symptoms_en"]
    cult = record["cultural_practices_ta" if lang == "ta" else "cultural_practices_en"]

    # Shared, always-safe context. Note what is NOT here.
    context = {
        "crop": record["crop_ta"] if lang == "ta" else record["crop"],
        "disease": record["disease_ta"] if lang == "ta" else record["disease"],
        "pathogen": record["pathogen"],
        "confidence": round(confidence, 3),
        "severity": severity,
        "symptoms": sym,
        "cultural_practices": cult,
        "language": lang,
    }

    if prescriptive:
        context["chemical_interventions"] = record["chemical_interventions"]
        context["source"] = record["source_institution"]
        context["source_url"] = record["source_url"]
        context["instruction"] = (
            "Rewrite the information above as simple advice a smallholder farmer can "
            "act on. Use ONLY what is given. Do not add any chemical, dose, interval "
            "or product that does not appear above. State the confidence plainly."
        )
        mode, reason = "prescriptive", "confident_and_sourced"
    else:
        context["instruction"] = (
            "Describe the likely condition and the preventive practices above. "
            "You have NOT been given any chemical treatment and must not name one. "
            "Tell the farmer to confirm with the local agricultural extension officer "
            "before applying anything."
        )
        mode = "abstain"
        if not confident and not verified_chemicals:
            reason = "low_confidence_and_unverified_record"
        elif not confident:
            reason = "low_confidence"
        else:
            reason = "record_not_source_verified"

    return {
        "advisory_mode": mode,
        "reason": reason,
        "confidence": confidence,
        "threshold": threshold,
        "record_id": record["id"],
        "prompt_context": context,
    }


# --------------------------------------------------------------------------
# self-test: the safety property, asserted
# --------------------------------------------------------------------------
CHEMICAL_KEYS = ("chemical_interventions", "dose", "dosage", "spray_interval")


def self_test(kb_path: Path) -> int:
    kb = KnowledgeBase(kb_path)
    print(f"knowledge base coverage: {kb.coverage()}")
    failures = []

    cases = [
        ("Tomato___Early_blight", 0.99, "high confidence, unverified record"),
        ("Tomato___Early_blight", 0.40, "low confidence, unverified record"),
        ("Tomato___Late_blight", 0.95, "high confidence, unverified record"),
        ("Tomato___healthy", 0.98, "high confidence, sourced but no chemicals"),
        ("Tomato___Septoria_leaf_spot", 0.72, "just above threshold, unverified"),
        ("Tomato___Does_Not_Exist", 0.99, "unknown class"),
    ]

    for label, conf, desc in cases:
        out = retrieve(kb, label, conf)
        ctx = out["prompt_context"]
        leaked = [k for k in CHEMICAL_KEYS if k in ctx]
        ok = (out["advisory_mode"] == "prescriptive") or not leaked
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures.append((label, conf, leaked))
        print(f"  [{status}] {label:<32} conf={conf:<5} -> {out['advisory_mode']:<12} "
              f"({out['reason']}) | chem keys in prompt: {leaked or 'none'}  # {desc}")

    print("\n  Tamil path:")
    ta = retrieve(kb, "Tomato___Late_blight", 0.95, severity="severe", lang="ta")
    ctx = ta["prompt_context"]
    print(f"  mode={ta['advisory_mode']}  disease={ctx['disease']}")
    print(f"  first symptom: {ctx['symptoms'][0]}")
    if any(k in ctx for k in CHEMICAL_KEYS):
        failures.append(("tamil", 0.95, "chemical leak"))

    # a record that IS verified must pass chemicals through
    print("\n  Positive control (synthetic verified record):")
    kb.records["__test__"] = {
        "id": "test", "crop": "Test", "crop_ta": "Test", "disease": "Test",
        "disease_ta": "Test", "pathogen": "Test", "class_label": "__test__",
        "symptoms_en": ["x"], "symptoms_ta": ["x"],
        "cultural_practices_en": ["y"], "cultural_practices_ta": ["y"],
        "chemical_interventions": [{"name": "VERIFIED_EXAMPLE", "dose": "1 g/L"}],
        "sourced": True, "source_institution": "Test", "source_url": "http://example.org",
        "identification_evidence": "", "verification_date": "2026-01-01",
        "region": "Test", "notes": "",
    }
    pos = retrieve(kb, "__test__", 0.99)
    passes = pos["advisory_mode"] == "prescriptive" and "chemical_interventions" in pos["prompt_context"]
    print(f"  [{'PASS' if passes else 'FAIL'}] verified record at high confidence -> "
          f"{pos['advisory_mode']}, chemicals present: "
          f"{'chemical_interventions' in pos['prompt_context']}")
    if not passes:
        failures.append(("positive_control", 0.99, "chemicals withheld from a verified record"))

    neg = retrieve(kb, "__test__", 0.30)
    withheld = neg["advisory_mode"] == "abstain" and "chemical_interventions" not in neg["prompt_context"]
    print(f"  [{'PASS' if withheld else 'FAIL'}] verified record at LOW confidence -> "
          f"{neg['advisory_mode']}, chemicals withheld: {withheld}")
    if not withheld:
        failures.append(("negative_control", 0.30, "chemicals leaked below threshold"))

    print()
    if failures:
        print(f"FAILED: {len(failures)} case(s): {failures}")
        return 1
    print("ALL PASS - no chemical text reaches the prompt in any abstain path.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=str(DEFAULT_KB))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--class-label")
    ap.add_argument("--confidence", type=float, default=0.9)
    ap.add_argument("--lang", default="en", choices=["en", "ta"])
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test(Path(args.kb)))
    if args.class_label:
        kb = KnowledgeBase(Path(args.kb))
        print(json.dumps(retrieve(kb, args.class_label, args.confidence, lang=args.lang),
                         indent=2, ensure_ascii=False))
    else:
        ap.print_help()
