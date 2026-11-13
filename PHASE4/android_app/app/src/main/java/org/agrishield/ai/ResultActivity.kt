package org.agrishield.ai

import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch
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
                vm.state.collect { render(it) }
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

    companion object {
        const val EXTRA_URI = "uri"
    }
}
