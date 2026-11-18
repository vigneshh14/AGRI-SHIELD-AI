package org.agrishield.ai

import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch
import com.agrishield.advisory.AdvisoryGate
import com.agrishield.advisory.Decision
import com.agrishield.advisory.KbRecord
import org.agrishield.ai.databinding.ActivityResultBinding
import org.agrishield.ai.preprocess.AgriShieldPreprocess

/**
 * Renders [ResultViewModel.state]. Holds no threads, no model, and no
 * full-resolution image: all of that lives in the ViewModel, which survives
 * rotation and releases the model safely when the screen is finished.
 *
 * Presents output as a model prediction, never a diagnosis, and shows all four
 * probabilities — a 0.34/0.33 split and a 0.99 both look like "top-1"
 * otherwise, and they mean entirely different things.
 */
class ResultActivity : AppCompatActivity() {

    private lateinit var b: ActivityResultBinding
    private val vm: ResultViewModel by viewModels()

    private val prettyNames = mapOf(
        "Tomato___Early_blight" to "Tomato — Early Blight",
        "Tomato___Late_blight" to "Tomato — Late Blight",
        "Tomato___Septoria_leaf_spot" to "Tomato — Septoria Leaf Spot",
        "Tomato___healthy" to "Tomato — Healthy Leaf"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityResultBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.btnBack.setOnClickListener { finish() }

        val uriStr = intent.getStringExtra(EXTRA_URI)
        if (uriStr == null) { finish(); return }

        vm.start(uriStr)            // idempotent: no second inference after rotation

        lifecycleScope.launch {
            // Collection stops below STARTED and is cancelled on destroy, so a
            // late result can never touch a dead activity.
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { vm.state.collect { render(it) } }
                launch { vm.advisory.collect { renderAdvisory(it) } }
            }
        }
    }

    private fun render(s: ResultViewModel.UiState) = when (s) {
        is ResultViewModel.UiState.Idle -> showWorking(null, "Starting…")
        is ResultViewModel.UiState.Working -> showWorking(s.thumbnail, s.stage)
        is ResultViewModel.UiState.Success -> showSuccess(s)
        is ResultViewModel.UiState.Failure -> showFailure(s)
    }

    private fun showWorking(thumb: android.graphics.Bitmap?, stage: String) {
        b.progress.visibility = View.VISIBLE
        b.groupResult.visibility = View.VISIBLE
        if (thumb != null) b.imgResult.setImageBitmap(thumb)
        b.txtPrediction.text = ""
        b.txtConfidence.text = ""
        b.txtProbs.text = ""
        b.txtLatency.text = ""
        b.txtStatus.text = stage
        b.txtUncertain.visibility = View.GONE
        b.txtCropWarning.visibility = View.GONE
    }

    private fun showSuccess(s: ResultViewModel.UiState.Success) {
        val p = s.prediction
        b.progress.visibility = View.GONE
        b.groupResult.visibility = View.VISIBLE
        b.imgResult.setImageBitmap(s.thumbnail)

        b.txtPrediction.text = prettyNames[p.label] ?: p.label
        b.txtConfidence.text = "%.1f%% model confidence".format(p.confidence * 100)

        b.txtProbs.text = AgriShieldPreprocess.CLASSES.indices.joinToString("\n") { i ->
            val name = AgriShieldPreprocess.CLASSES[i]
            val bar = "█".repeat((p.probabilities[i] * 20).toInt().coerceIn(0, 20))
            "%-28s %6.2f%%  %s".format(prettyNames[name] ?: name, p.probabilities[i] * 100, bar)
        }

        b.txtLatency.text = ("Inference %.1f ms  •  preprocessing %.1f ms\n" +
            "on-device  •  ExecuTorch / XNNPACK").format(p.latencyMs, p.preprocessMs)

        b.txtStatus.text = buildString {
            append("Model loaded and hash-verified  •  ${s.input.sourceWidth} x ${s.input.sourceHeight}")
            if (s.input.exifOrientation != 1) append("  •  EXIF orientation corrected")
            s.input.colorSpaceNote?.let { append("\n").append(it) }
        }

        // Low top-1, or a near-tie with the runner-up: do not rely on this.
        val shaky = p.confidence < 0.60f || p.margin < 0.20f
        b.txtUncertain.visibility = if (shaky) View.VISIBLE else View.GONE
        b.txtCropWarning.visibility =
            if (s.input.retainedAreaFraction < 0.60) View.VISIBLE else View.GONE
    }

    private fun showFailure(s: ResultViewModel.UiState.Failure) {
        b.progress.visibility = View.GONE
        b.groupResult.visibility = View.VISIBLE
        if (s.thumbnail != null) b.imgResult.setImageBitmap(s.thumbnail)
        b.txtPrediction.text = s.title
        b.txtConfidence.text = ""
        b.txtProbs.text = s.detail
        b.txtLatency.text = ""
        b.txtStatus.text = "No prediction was produced."
        b.txtUncertain.visibility = View.GONE
        b.txtCropWarning.visibility = View.GONE
    }

    private fun renderAdvisory(a: ResultViewModel.AdvisoryState) {
        when (a) {
            is ResultViewModel.AdvisoryState.NotStarted -> {
                b.txtAdvisory.text = ""
                b.txtAdvisorySource.text = ""
                b.txtTreatment.visibility = View.GONE
            }
            is ResultViewModel.AdvisoryState.ModelMissing -> {
                b.txtAdvisory.text = getString(R.string.advisory_missing)
                b.txtAdvisorySource.text = a.dir
                b.txtTreatment.visibility = View.GONE
            }
            is ResultViewModel.AdvisoryState.Generating -> {
                b.txtAdvisory.text = a.textSoFar.replace(Regex("<\\|[^|]*\\|>"), "")
                b.txtAdvisorySource.text = getString(R.string.advisory_generating)
                showTreatment(a.decision)
            }
            is ResultViewModel.AdvisoryState.Done -> {
                val r = a.result
                b.txtAdvisory.text = r.shownText
                b.txtAdvisorySource.text = getString(
                    if (r.fromLlama) R.string.advisory_badge_llama else R.string.advisory_badge_fallback
                ) + "  •  %.1f s".format(r.wallMs / 1000.0)
                showTreatment(r.decision)
            }
            is ResultViewModel.AdvisoryState.Failed -> {
                b.txtAdvisory.text = a.decision?.let { AdvisoryGate.fallbackText(it) } ?: ""
                b.txtAdvisorySource.text = "Llama could not run: ${a.message}"
                showTreatment(a.decision)
            }
        }
    }

    /**
     * Products and doses come only from the TNAU record, never from model text,
     * and only when the gate decided to advise.
     */
    private fun showTreatment(d: Decision?) {
        val r: KbRecord? = (d as? Decision.Advise)?.record
        if (r == null) {
            b.txtTreatment.visibility = View.VISIBLE
            b.txtTreatment.text = "No product is recommended for this result.\n" +
                ((d as? Decision.Abstain)?.reason?.let { "Reason: $it" } ?: "")
            return
        }
        b.txtTreatment.visibility = View.VISIBLE
        b.txtTreatment.text = buildString {
            append("${r.disease} (${r.diseaseTa})")
            r.pathogen?.let { append("\nPathogen: $it") }
            if (r.biological.isNotEmpty()) {
                append("\n\nBiological")
                r.biological.forEach { append("\n  ${it.agent}, ${it.use}: ${it.dose}") }
            }
            if (r.chemicals.isNotEmpty()) {
                append("\n\nChemical (use ONE)")
                r.chemicals.forEach { append("\n  ${it.active}: ${it.dose}") }
                r.chemicalNote?.let { append("\n$it") }
                append("\n\n${AdvisoryGate.NO_INTERVAL_TEXT}")
            }
            append("\n\nField practice")
            r.culturalEn.forEach { append("\n  - $it") }
            r.sourceUrl?.let { append("\n\nSource: ${r.sourceInstitution}\n$it\nVerified ${r.verifiedOn}") }
        }
    }

    companion object {
        const val EXTRA_URI = "uri"
    }
}
