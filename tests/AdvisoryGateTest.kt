package com.agrishield.advisory

import org.pytorch.executorch.extension.llm.LlmModule
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

var passed = 0
fun t(name: String, cond: Boolean) {
    if (!cond) throw AssertionError("FAIL: $name")
    passed++; println("PASS  $name")
}

fun allChemTerms(): List<String> =
    KnowledgeBase.records.flatMap { r -> r.chemicals.flatMap { c -> listOf(c.active, c.dose) } }

fun main() {
    val kb = KnowledgeBase.records
    t("KB has 4 records", kb.size == 4)
    t("every chemical-bearing record is sourced with URL",
        kb.filter { it.chemicals.isNotEmpty() }.all { it.sourced && it.sourceUrl!!.startsWith("https://agritech.tnau.ac.in/") })
    t("early blight has 9 TNAU products", KnowledgeBase.byClassLabel("Tomato___Early_blight")!!.chemicals.size == 9)

    // decide()
    t("confident early blight -> Advise", AdvisoryGate.decide("Tomato___Early_blight", 0.95f) is Decision.Advise)
    t("exactly at threshold -> Advise", AdvisoryGate.decide("Tomato___Late_blight", AdvisoryGate.DEFAULT_THRESHOLD) is Decision.Advise)
    t("just below threshold -> Abstain", AdvisoryGate.decide("Tomato___Late_blight", 0.7999f) is Decision.Abstain)
    t("unknown label -> Abstain", AdvisoryGate.decide("Potato___Late_blight", 0.99f) is Decision.Abstain)
    val unsourced = kb.map { if (it.id == "tomato_late_blight") it.copy(sourced = false) else it }
    t("unsourced record -> Abstain even at 0.99", AdvisoryGate.decide("Tomato___Late_blight", 0.99f, unsourced) is Decision.Abstain)
    t("NaN confidence rejected", runCatching { AdvisoryGate.decide("Tomato___healthy", Float.NaN) }.isFailure)
    t("confidence > 1 rejected", runCatching { AdvisoryGate.decide("Tomato___healthy", 1.5f) }.isFailure)

    // Prompt never carries chemical names or doses, for every class x confidence sweep.
    val terms = allChemTerms().map { it.lowercase() } + listOf("ml/ac", "g/ac", "kg/ac", "ml/ha")
    var prompts = 0
    for (r in kb) for (c in listOf(0f, 0.3f, 0.5f, 0.79f, 0.8f, 0.9f, 1f)) {
        val p = AdvisoryGate.buildPrompt(AdvisoryGate.decide(r.classLabel, c)).lowercase()
        val leak = terms.firstOrNull { p.contains(it) }
        t("prompt ${r.id}@$c leaks nothing", leak == null); prompts++
    }
    val ab = AdvisoryGate.buildPrompt(AdvisoryGate.decide("Tomato___Early_blight", 0.4f))
    t("abstain prompt says do not spray", ab.contains("should not spray"))
    t("abstain prompt omits disease name", !ab.contains("Early Blight"))
    val adv = AdvisoryGate.buildPrompt(AdvisoryGate.decide("Tomato___Early_blight", 0.9f))
    t("advise prompt uses Llama 3 template", adv.startsWith("<|begin_of_text|><|start_header_id|>system") && adv.endsWith("<|start_header_id|>assistant<|end_header_id|>\n\n"))
    t("advise prompt has pathogen", adv.contains("Alternaria solani"))
    t("advise prompt states no interval", adv.contains("does not give a spray interval"))

    // guard()
    val clean = "Early blight is a fungal disease of tomato. Look for brown spots with rings. Remove and destroy old crop debris and rotate crops. Use only the product shown in the app."
    t("clean text accepted", AdvisoryGate.guard(clean).accepted)
    t("KB chemical name rejected", !AdvisoryGate.guard("Spray Mancozeb on the leaves.").accepted)
    t("non-KB pesticide rejected", !AdvisoryGate.guard("Use carbendazim right away.").accepted)
    t("combo ingredient rejected", !AdvisoryGate.guard("Try difenoconazole.").accepted)
    t("dose rejected", !AdvisoryGate.guard("Mix 2 g per litre of water.").accepted)
    t("ml dose rejected", !AdvisoryGate.guard("Apply 200 ml in the field.").accepted)
    t("percentage rejected", !AdvisoryGate.guard("Use the 75% powder.").accepted)
    t("interval rejected", !AdvisoryGate.guard("Spray every 10 days.").accepted)
    t("day range rejected", !AdvisoryGate.guard("Repeat after 7-10 days.").accepted)
    t("empty rejected", !AdvisoryGate.guard("<|eot_id|>").accepted)
    t("special tokens stripped", AdvisoryGate.guard("Remove infected leaves.<|eot_id|>").text == "Remove infected leaves.")
    for (r in kb) for (c in listOf(0.2f, 0.95f)) {
        val d = AdvisoryGate.decide(r.classLabel, c)
        val g = AdvisoryGate.guard(AdvisoryGate.fallbackText(d))
        t("fallback ${r.id}@$c passes its own guard ${g.violations}", g.accepted)
    }

    // Engine end-to-end with the stub runtime.
    val dir = kotlin.io.path.createTempDirectory("agri").toFile()
    val pte = File(dir, "m.pte").apply { writeText("x") }
    val tok = File(dir, "tokenizer.model").apply { writeText("x") }

    fun run(label: String, conf: Float, script: List<String>): LlamaAdvisoryEngine.Result {
        LlmModule.script = script
        val e = LlamaAdvisoryEngine(pte, tok)
        val latch = CountDownLatch(1)
        var res: LlamaAdvisoryEngine.Result? = null
        var err: Throwable? = null
        val toks = mutableListOf<String>()
        e.advise(label, conf, { toks += it }, { res = it; latch.countDown() }, { err = it; latch.countDown() })
        check(latch.await(5, TimeUnit.SECONDS)) { "timeout" }
        e.close()
        err?.let { throw it }
        check(toks == script) { "streamed tokens differ" }
        return res!!
    }
    val ok = run("Tomato___Early_blight", 0.93f, listOf("Early blight ", "is a fungal ", "disease. Remove ", "crop debris."))
    t("engine: clean output shown from Llama", ok.fromLlama && ok.shownText.startsWith("Early blight"))
    t("engine: echo=false, seqLen=768", !LlmModule.lastEcho && LlmModule.lastSeqLen == 768)
    t("engine: stats captured", ok.statsJson!!.contains("generated_tokens"))
    val bad = run("Tomato___Late_blight", 0.97f, listOf("Spray ", "Zineb 75% ", "every 7 days."))
    t("engine: hallucinated dose -> fallback", !bad.fromLlama && bad.violations.isNotEmpty() && !bad.shownText.contains("Zineb"))
    val low = run("Tomato___Late_blight", 0.41f, listOf("I am not sure. ", "Please ask the officer."))
    t("engine: low confidence -> Abstain decision", low.decision is Decision.Abstain)
    t("engine: abstain prompt reached model without chemicals", allChemTerms().none { LlmModule.lastPrompt!!.contains(it) })
    t("engine: close frees native memory", LlmModule.resetCalls >= 3)
    val missing = runCatching {
        val e = LlamaAdvisoryEngine(File(dir, "nope.pte"), tok)
        val latch = CountDownLatch(1); var err: Throwable? = null
        e.advise("Tomato___healthy", 0.9f, {}, { latch.countDown() }, { err = it; latch.countDown() })
        latch.await(5, TimeUnit.SECONDS); e.close(); err
    }.getOrNull()
    t("engine: missing model reported via onError", missing?.message?.contains("Llama model missing") == true)

    println("\nALL $passed CHECKS PASSED ($prompts prompt-leak sweeps)")
}
