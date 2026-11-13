package com.agrishield.advisory

/*
 * M6 safety gate + M5 prompt builder + output guard, for the Android app.
 * Pure Kotlin: no Android imports, so it is unit-tested on a plain JVM.
 *
 * Safety property (same as the Python M6 module):
 *   A chemical name or dose can reach Llama's prompt ONLY when
 *     (a) classifier confidence >= threshold, AND
 *     (b) the matched record is sourced = true with a source URL.
 *   In every other case the prompt is built from a record copy whose
 *   chemical list is empty, so there is nothing for the model to repeat.
 *
 * Doses are never taken from Llama's text. The UI shows them from the
 * knowledge base in a separate table (see Decision.Advise.record.chemicals).
 */

data class Chemical(val active: String, val dose: String)
data class Biological(val agent: String, val use: String, val dose: String)

data class KbRecord(
    val id: String,
    val classLabel: String,
    val crop: String,
    val cropTa: String,
    val disease: String,
    val diseaseTa: String,
    val pathogen: String?,
    val symptomsEn: List<String>,
    val culturalEn: List<String>,
    val biological: List<Biological>,
    val chemicals: List<Chemical>,
    val chemicalNote: String?,
    val sourced: Boolean,
    val sourceInstitution: String,
    val sourceUrl: String?,
    val verifiedOn: String?,
)

sealed class Decision {
    /** Confident, sourced: Llama may explain; KB table shows doses. */
    data class Advise(val record: KbRecord, val confidence: Float) : Decision()

    /** Not confident or not sourced: no chemical information anywhere. */
    data class Abstain(val reason: String, val topLabel: String, val confidence: Float) : Decision()
}

object AdvisoryGate {
    /** Keep equal to the threshold used in the Python M6 module and the report. */
    const val DEFAULT_THRESHOLD = 0.80f

    const val NO_INTERVAL_TEXT =
        "TNAU does not give a spray interval for this disease. Confirm timing with your " +
            "local agriculture extension officer and follow the product label."

    fun decide(
        topLabel: String,
        confidence: Float,
        kb: List<KbRecord> = KnowledgeBase.records,
        threshold: Float = DEFAULT_THRESHOLD,
    ): Decision {
        require(confidence.isFinite() && confidence in 0f..1f) { "confidence must be in [0,1]" }
        val rec = kb.firstOrNull { it.classLabel == topLabel }
            ?: return Decision.Abstain("unknown class '$topLabel'", topLabel, confidence)
        if (confidence < threshold) {
            return Decision.Abstain(
                "confidence ${"%.2f".format(confidence)} below ${"%.2f".format(threshold)}",
                topLabel, confidence,
            )
        }
        if (!rec.sourced || (rec.chemicals.isNotEmpty() && rec.sourceUrl == null)) {
            return Decision.Abstain("record '${rec.id}' is not source-verified", topLabel, confidence)
        }
        return Decision.Advise(rec, confidence)
    }

    private const val SYSTEM =
        "You are an agricultural assistant for small farmers in Tamil Nadu. " +
            "Use ONLY the facts given by the user. Do not add any disease, pest, chemical, " +
            "product, dose, or timing that is not in the facts. Do not write any chemical " +
            "names or doses: the app shows them separately from the official source. " +
            "Write 4 to 6 short, simple sentences in English."

    /** Llama 3 instruct chat template, as used by the ExecuTorch Llama demo app. */
    fun buildPrompt(d: Decision): String {
        val user = when (d) {
            is Decision.Advise -> buildString {
                val r = d.record
                appendLine("FACTS")
                appendLine("Crop: ${r.crop}")
                appendLine("Diagnosis: ${r.disease}" + (r.pathogen?.let { " (caused by $it)" } ?: ""))
                appendLine("Symptoms: " + r.symptomsEn.joinToString("; "))
                appendLine("Field practices: " + r.culturalEn.joinToString("; "))
                if (r.chemicals.isNotEmpty()) {
                    appendLine("Chemical control: officially recommended products exist and are shown in the app.")
                    appendLine("Timing: $NO_INTERVAL_TEXT")
                }
                appendLine()
                append("Explain to the farmer what this disease is, how to recognise it, and what field practices to follow now.")
            }
            is Decision.Abstain -> buildString {
                appendLine("FACTS")
                appendLine("The app could not identify the problem on this leaf with enough confidence.")
                appendLine()
                append(
                    "Tell the farmer politely that the result is uncertain, that they should not spray " +
                        "anything based on this result, and that they should retake the photo in daylight " +
                        "with one leaf filling the frame, or show the plant to the local agriculture " +
                        "extension officer."
                )
            }
        }
        return "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n$SYSTEM<|eot_id|>" +
            "<|start_header_id|>user<|end_header_id|>\n\n$user<|eot_id|>" +
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
    }

    /**
     * Pesticide names the guard watches for even if they are not in our KB, so a
     * hallucinated product is caught. Lower-case single words / stems.
     */
    private val EXTRA_PESTICIDE_TERMS = listOf(
        "carbendazim", "chlorothalonil", "copper oxychloride", "copper hydroxide", "metalaxyl",
        "propineb", "hexaconazole", "propiconazole", "thiophanate", "captan", "sulphur", "sulfur",
        "imidacloprid", "thiamethoxam", "acetamiprid", "chlorpyrifos", "dimethoate", "profenofos",
        "cypermethrin", "lambda", "emamectin", "spinosad", "fipronil", "streptomycin", "streptocycline",
        "validamycin", "tricyclazole", "dithane", "bavistin", "ridomil", "kavach",
    )

    private fun ingredientTerms(kb: List<KbRecord>): Set<String> =
        kb.flatMap { r -> r.chemicals.flatMap { c -> c.active.lowercase().split("+") } }
            .map { it.replace(Regex("[0-9.%/]+|\\b(sc|wp|wg|ec|g|l)\\b"), " ").trim() }
            .filter { it.length >= 4 }
            .toSet()

    private val DOSE = Regex(
        "\\d+(?:[.,]\\d+)?\\s*(?:-\\s*\\d+(?:[.,]\\d+)?\\s*)?" +
            "(?:%|ml|millilit|g\\b|gm|gram|kg|kilo|litre|liter|l/)",
        RegexOption.IGNORE_CASE,
    )

    private val INTERVAL = Regex(
        "\\b(?:every|once in|interval of)\\s+\\d+|\\d+\\s*(?:-\\s*\\d+\\s*)?days?\\b",
        RegexOption.IGNORE_CASE,
    )

    data class GuardResult(val accepted: Boolean, val text: String, val violations: List<String>)

    /**
     * Rejects model output that names any chemical, states any dose, or states any
     * spray interval. Llama is told not to, so any of these is a hallucination risk.
     */
    fun guard(raw: String, kb: List<KbRecord> = KnowledgeBase.records): GuardResult {
        val text = raw.replace(Regex("<\\|[^|]*\\|>"), "").trim()
        val lower = text.lowercase()
        val v = mutableListOf<String>()
        (ingredientTerms(kb) + EXTRA_PESTICIDE_TERMS).forEach { if (lower.contains(it)) v += "chemical:$it" }
        DOSE.findAll(text).forEach { v += "dose:${it.value}" }
        INTERVAL.findAll(text).forEach { v += "interval:${it.value}" }
        if (text.isBlank()) v += "empty"
        return GuardResult(v.isEmpty(), text, v)
    }

    /** Deterministic text shown if the guard rejects Llama's output. Marked so the UI can label it. */
    fun fallbackText(d: Decision): String = when (d) {
        is Decision.Advise -> "${d.record.disease} detected on ${d.record.crop}. " +
            "Symptoms: ${d.record.symptomsEn.first()}. " +
            "Do now: ${d.record.culturalEn.joinToString("; ")}."
        is Decision.Abstain -> "The result is uncertain. Do not spray based on this photo. " +
            "Retake the photo in daylight with one leaf filling the frame, or consult your " +
            "local agriculture extension officer."
    }
}
