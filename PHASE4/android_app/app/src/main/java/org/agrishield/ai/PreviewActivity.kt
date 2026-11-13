package org.agrishield.ai

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.agrishield.ai.databinding.ActivityPreviewBinding
import org.agrishield.ai.ml.ImageLoader

/**
 * Shows the chosen photograph and lets the user confirm before inference.
 *
 * Uses ImageLoader.loadPreview — a small, display-only decode, off the main
 * thread. The previous version ran the FULL-resolution model pipeline here, on
 * the main thread (an ANR risk on a 12 MP photo), and then ran it again on the
 * result screen. The model input is now built exactly once, in ResultViewModel.
 */
class PreviewActivity : AppCompatActivity() {

    private lateinit var b: ActivityPreviewBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityPreviewBinding.inflate(layoutInflater)
        setContentView(b.root)

        val uriStr = intent.getStringExtra(EXTRA_URI)
        if (uriStr == null) { finish(); return }

        b.btnBack.setOnClickListener { finish() }
        b.btnRun.isEnabled = false
        b.txtMeta.text = "Loading preview…"

        // lifecycleScope is cancelled on destroy, so the UI update below can
        // never reach a destroyed activity.
        lifecycleScope.launch {
            try {
                val info = withContext(Dispatchers.IO) {
                    ImageLoader.loadPreview(this@PreviewActivity, Uri.parse(uriStr))
                }
                b.imgPreview.setImageBitmap(info.thumbnail)
                b.txtMeta.text = buildString {
                    append("${info.sourceWidth} x ${info.sourceHeight}")
                    if (info.exifApplied) append("  •  EXIF orientation corrected")
                    append("\nThe model sees the centre %.0f%% of this frame"
                        .format(info.retainedAreaFraction * 100))
                }
                // The model only ever sees a centre square. Say so when it
                // matters, rather than letting a cropped-away lesion look like
                // a model error.
                b.txtCropWarning.visibility =
                    if (info.retainedAreaFraction < 0.60) View.VISIBLE else View.GONE
                b.btnRun.isEnabled = true
                b.btnRun.setOnClickListener {
                    startActivity(Intent(this@PreviewActivity, ResultActivity::class.java).apply {
                        putExtra(ResultActivity.EXTRA_URI, uriStr)
                    })
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ImageLoader.ImageMemoryException) {
                b.txtMeta.text = e.userMessage
            } catch (e: Exception) {
                b.txtMeta.text = "Could not read this image.\n${e.message}"
            } catch (e: OutOfMemoryError) {
                b.txtMeta.text = "Not enough memory to preview this image."
            }
        }
    }

    companion object { const val EXTRA_URI = "uri" }
}
