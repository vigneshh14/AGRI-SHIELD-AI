package org.agrishield.ai

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.agrishield.ai.databinding.ActivityMainBinding
import java.io.File
import java.io.IOException

/**
 * Home screen: choose a photograph from the gallery, or take one.
 *
 * Camera permission. ActivityResultContracts.TakePicture dispatches
 * MediaStore.ACTION_IMAGE_CAPTURE, which hands control to the system camera.
 * That needs android.permission.CAMERA only if this app DECLARES it — and once
 * declared, the runtime grant becomes mandatory. This app declares none, so
 * none is requested. (An earlier version requested CAMERA without declaring it,
 * which always returns "denied" and made capture impossible.)
 *
 * Process death during capture. While the camera app is in front, Android may
 * kill this process to reclaim memory — common on a loaded phone. The pending
 * capture path is therefore saved in instance state, so a photo that was taken
 * is not reported as "not captured" when the activity is recreated.
 *
 * Gallery images are copied byte-for-byte into private storage on selection.
 * GetContent grants a read permission that is not persistable and can lapse if
 * the process dies between screens; a private copy removes that dependency.
 * The copy is byte-identical, so the pixels the model sees are unchanged.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding

    /** Absolute path of the file the camera app is writing into, if any. */
    private var pendingCapturePath: String? = null

    private val pickImage = registerForActivityResult(
        ActivityResultContracts.GetContent()) { uri -> uri?.let { importFromGallery(it) } }

    private val takePicture = registerForActivityResult(
        ActivityResultContracts.TakePicture()) { saved ->
        val path = pendingCapturePath
        pendingCapturePath = null
        val f = path?.let { File(it) }
        when {
            f == null -> toast("No photo was captured.")
            saved && f.length() > 0L -> openPreview(Uri.fromFile(f))
            else -> {
                f.delete()       // cancelled: don't leave empty files in cache
                toast("No photo was captured.")
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        pendingCapturePath = savedInstanceState?.getString(STATE_PENDING_CAPTURE)

        b.btnSelect.setOnClickListener {
            // "image/*" rather than a MIME list: some gallery apps filter
            // HEIC/WEBP out of a narrow list and show an empty picker.
            try { pickImage.launch("image/*") }
            catch (e: ActivityNotFoundException) { toast("No gallery app is available.") }
        }
        b.btnCapture.setOnClickListener { launchCamera() }
        b.btnAbout.setOnClickListener { startActivity(Intent(this, AboutActivity::class.java)) }

        if (savedInstanceState == null) {
            // Fresh start: clear stale working copies. Never the pending capture.
            val keep = pendingCapturePath
            lifecycleScope.launch(Dispatchers.IO) { purgeOld(keep) }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString(STATE_PENDING_CAPTURE, pendingCapturePath)
    }

    private fun launchCamera() {
        val f = File(dir(CAPTURE_DIR), "capture_${System.currentTimeMillis()}.jpg")
        val uri = try {
            FileProvider.getUriForFile(this, "$packageName.fileprovider", f)
        } catch (e: IllegalArgumentException) {
            // file_paths.xml does not cover this directory.
            toast("Camera storage is misconfigured: ${e.message}")
            return
        }
        pendingCapturePath = f.absolutePath
        try {
            takePicture.launch(uri)
        } catch (e: ActivityNotFoundException) {
            pendingCapturePath = null
            toast("No camera app is available on this device.")
        }
    }

    private fun importFromGallery(src: Uri) {
        lifecycleScope.launch {
            try {
                val copy = withContext(Dispatchers.IO) { copyToPrivate(src) }
                openPreview(Uri.fromFile(copy))
            } catch (e: CancellationException) {
                throw e
            } catch (e: IOException) {
                toast(e.message ?: "Could not read the selected image.")
            } catch (e: SecurityException) {
                toast("Permission to read that image was refused.")
            }
        }
    }

    /** Byte-for-byte copy, so the decoded pixels are identical to the original. */
    private fun copyToPrivate(src: Uri): File {
        val out = File(dir(IMPORT_DIR), "import_${System.currentTimeMillis()}")
        val tmp = File(out.path + ".partial")
        try {
            val input = contentResolver.openInputStream(src)
                ?: throw IOException("Could not open the selected image.")
            input.use { ins ->
                tmp.outputStream().use { os ->
                    val buf = ByteArray(1 shl 16)
                    var total = 0L
                    while (true) {
                        val n = ins.read(buf)
                        if (n < 0) break
                        total += n
                        // Fail cleanly rather than fill a nearly-full phone.
                        if (total > MAX_IMPORT_BYTES) {
                            throw IOException("That file is larger than ${MAX_IMPORT_BYTES / 1_000_000} MB.")
                        }
                        if (tmp.parentFile!!.usableSpace < MIN_FREE_BYTES) {
                            throw IOException("The phone is too low on storage to import this image.")
                        }
                        os.write(buf, 0, n)
                    }
                    if (total == 0L) throw IOException("The selected file is empty.")
                }
            }
            if (!tmp.renameTo(out)) throw IOException("Could not store the imported image.")
            return out
        } catch (e: Exception) {
            tmp.delete()
            throw e
        }
    }

    private fun purgeOld(keepPath: String?) {
        val cutoff = System.currentTimeMillis() - MAX_AGE_MS
        for (d in listOf(dir(CAPTURE_DIR), dir(IMPORT_DIR))) {
            d.listFiles()?.forEach { f ->
                if (f.absolutePath != keepPath && f.lastModified() < cutoff) f.delete()
            }
        }
    }

    private fun dir(name: String) = File(cacheDir, name).apply { mkdirs() }

    private fun openPreview(uri: Uri) {
        startActivity(Intent(this, PreviewActivity::class.java).apply {
            putExtra(PreviewActivity.EXTRA_URI, uri.toString())
        })
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_LONG).show()

    companion object {
        private const val STATE_PENDING_CAPTURE = "pending_capture_path"
        /** Must match <cache-path path="captures/"> in res/xml/file_paths.xml. */
        private const val CAPTURE_DIR = "captures"
        /** Private only; never shared, so it needs no FileProvider entry. */
        private const val IMPORT_DIR = "imports"
        private const val MAX_AGE_MS = 24L * 60 * 60 * 1000
        private const val MAX_IMPORT_BYTES = 200_000_000L
        private const val MIN_FREE_BYTES = 50_000_000L
    }
}
