package org.agrishield.ai.ml

import android.app.ActivityManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import org.agrishield.ai.preprocess.AgriShieldPreprocess
import org.agrishield.ai.preprocess.MemoryPlan
import org.agrishield.ai.preprocess.OrientedRgb
import java.io.InputStream

/**
 * Two deliberately separate decode paths.
 *
 *  loadForInference() — full resolution, exactly the pixels the Python reference
 *    would see. Used only to build the model input. Never downsampled. Refuses
 *    up front, with a readable message, if the image cannot fit in memory.
 *
 *  loadPreview() — a small, display-only bitmap for the screen. Free to use
 *    inSampleSize and createScaledBitmap because the model never sees it.
 *
 * Earlier versions ran the full-resolution pipeline twice per photograph (once
 * for the preview screen, on the MAIN thread, and again for the result screen)
 * and kept a second full-resolution bitmap alive to apply EXIF rotation. All
 * three are gone.
 *
 * Resizing for the model happens only in AgriShieldPreprocess, which reproduces
 * Pillow bit-exactly. Bitmap.createScaledBitmap aliases badly on large
 * downscales (measured 0.8235 max abs diff on the normalised tensor) and is
 * never on the model path.
 */
object ImageLoader {

    /** The decode or conversion failed for a reason other than memory. */
    class ImageDecodeException(message: String, cause: Throwable? = null) :
        Exception(message, cause)

    /** The image is too large for available memory. [userMessage] is shown as-is. */
    class ImageMemoryException(val userMessage: String, cause: Throwable? = null) :
        Exception(userMessage, cause)

    data class InferenceInput(
        val img: AgriShieldPreprocess.Img,
        val sourceWidth: Int,
        val sourceHeight: Int,
        val exifOrientation: Int,
        val retainedAreaFraction: Double,
        /** Non-null when the decoder colour-managed a non-sRGB image (see below). */
        val colorSpaceNote: String?
    )

    data class PreviewInfo(
        /** Display only. Never fed to the model. */
        val thumbnail: Bitmap,
        val sourceWidth: Int,
        val sourceHeight: Int,
        val uprightWidth: Int,
        val uprightHeight: Int,
        val exifOrientation: Int,
        val retainedAreaFraction: Double
    ) {
        val exifApplied: Boolean get() = exifOrientation != OrientedRgb.NORMAL
    }

    // ------------------------------------------------------------ inference

    /**
     * Full-resolution decode for the model.
     *
     * Peak memory for a 4000x3000 photograph: one 48 MB native bitmap, plus a
     * 36 MB Java RGB array and a ~4 MB row strip. (Measured on a desktop JVM:
     * 42.2 MB Java heap.) The bitmap is recycled in a finally block, so it is
     * released even when conversion fails.
     *
     * @throws ImageMemoryException  image too large; message is user-facing
     * @throws ImageDecodeException  unreadable or corrupt
     */
    fun loadForInference(context: Context, uri: Uri): InferenceInput {
        val (w, h) = readBounds(context, uri)
        val orientation = readOrientation(context, uri)

        // Pre-flight: refuse before allocating anything large.
        val plan = MemoryPlan.of(w, h, orientation)
        when (val v = MemoryPlan.check(plan, javaHeapAvailable(), nativeAvailable(context))) {
            is MemoryPlan.Verdict.TooLarge -> throw ImageMemoryException(v.reason)
            MemoryPlan.Verdict.Ok -> Unit
        }

        val opts = BitmapFactory.Options().apply {
            inPreferredConfig = Bitmap.Config.ARGB_8888
            // Pillow's convert("RGB") drops alpha WITHOUT compositing, keeping the
            // stored RGB. A premultiplied bitmap would already have multiplied RGB
            // by alpha (and zeroed fully transparent pixels), which getPixels'
            // un-premultiply cannot undo exactly. JPEG has no alpha, so this only
            // matters for PNG/WebP with transparency. The bitmap is never drawn —
            // the one thing a non-premultiplied bitmap cannot do.
            inPremultiplied = false
            inSampleSize = 1    // never downsample the model input
        }

        val bmp: Bitmap = try {
            open(context, uri).use { BitmapFactory.decodeStream(it, null, opts) }
        } catch (e: OutOfMemoryError) {
            throw ImageMemoryException(memoryMessage(w, h), e)
        } ?: throw ImageDecodeException(
            "The image could not be decoded. The file may be corrupt or in an unsupported format.")

        try {
            if (bmp.config == Bitmap.Config.HARDWARE) {
                throw ImageDecodeException("Decoder returned a hardware bitmap; pixels are not readable.")
            }
            if (bmp.width != w || bmp.height != h) {
                throw ImageDecodeException(
                    "Decoder returned ${bmp.width}x${bmp.height}, expected ${w}x$h.")
            }

            // getPixels() returns sRGB. For sRGB or untagged images — what phone
            // cameras normally write — that is the stored value, matching Pillow,
            // which ignores ICC profiles. For an image tagged with another colour
            // space (e.g. Display P3) Android converts and Pillow does not, so the
            // model input would differ. That case is detected and reported, not hidden.
            val cs = bmp.colorSpace
            val note = if (cs == null || cs.isSrgb) null else
                "Image is tagged ${cs.name}; Android converted it to sRGB and the desktop " +
                "pipeline does not, so the model input may differ slightly from the reference."

            val img = try {
                OrientedRgb.extract(w, h, orientation,
                    OrientedRgb.RowSource { y, rows, dst -> bmp.getPixels(dst, 0, w, 0, y, w, rows) })
            } catch (e: OutOfMemoryError) {
                throw ImageMemoryException(memoryMessage(w, h), e)
            } catch (e: IllegalArgumentException) {
                throw ImageMemoryException(e.message ?: memoryMessage(w, h), e)
            }

            val (uw, uh) = OrientedRgb.orientedSize(w, h, orientation)
            return InferenceInput(img, w, h, orientation,
                OrientedRgb.retainedAreaFraction(uw, uh), note)
        } finally {
            bmp.recycle()     // release the 48 MB native buffer as early as possible
        }
    }

    // -------------------------------------------------------------- preview

    /**
     * Small decode for the screen. Cheap enough to run on every preview, and
     * reports the retained-area fraction from dimensions alone.
     */
    fun loadPreview(context: Context, uri: Uri, maxEdge: Int = 1024): PreviewInfo {
        val (w, h) = readBounds(context, uri)
        val orientation = readOrientation(context, uri)
        val opts = BitmapFactory.Options().apply {
            inPreferredConfig = Bitmap.Config.ARGB_8888
            inSampleSize = sampleSizeFor(w, h, maxEdge)   // display only
        }
        val small = try {
            open(context, uri).use { BitmapFactory.decodeStream(it, null, opts) }
        } catch (e: OutOfMemoryError) {
            throw ImageMemoryException("Not enough memory even to preview this image.", e)
        } ?: throw ImageDecodeException(
            "The image could not be decoded. The file may be corrupt or in an unsupported format.")

        val upright = rotateForDisplay(small, orientation)
        if (upright !== small) small.recycle()
        val thumb = scaleForDisplay(upright, maxEdge)
        if (thumb !== upright) upright.recycle()

        val (uw, uh) = OrientedRgb.orientedSize(w, h, orientation)
        return PreviewInfo(thumb, w, h, uw, uh, orientation,
            OrientedRgb.retainedAreaFraction(uw, uh))
    }

    // ------------------------------------------- kept for DecoderParityTest

    /**
     * Raw RGB of a bitmap with no orientation change. Retained so the existing
     * instrumented DecoderParityTest compiles unmodified; it goes through the
     * same OrientedRgb code the inference path uses.
     */
    fun toRgb(bmp: Bitmap): AgriShieldPreprocess.Img {
        val w = bmp.width
        return OrientedRgb.extract(w, bmp.height, OrientedRgb.NORMAL,
            OrientedRgb.RowSource { y, rows, dst -> bmp.getPixels(dst, 0, w, 0, y, w, rows) })
    }

    // -------------------------------------------------------------- helpers

    private fun readBounds(context: Context, uri: Uri): Pair<Int, Int> {
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        try {
            open(context, uri).use { BitmapFactory.decodeStream(it, null, o) }
        } catch (e: ImageDecodeException) {
            throw e
        } catch (e: Exception) {
            throw ImageDecodeException("The image could not be read: ${e.message}", e)
        }
        if (o.outWidth <= 0 || o.outHeight <= 0) {
            throw ImageDecodeException(
                "This file could not be read as an image. It may be corrupt, " +
                "or in a format this device cannot decode.")
        }
        return Pair(o.outWidth, o.outHeight)
    }

    /** Missing or unreadable EXIF is normal (most gallery images) and means NORMAL. */
    private fun readOrientation(context: Context, uri: Uri): Int = try {
        open(context, uri).use {
            OrientedRgb.normalise(ExifInterface(it).getAttributeInt(
                ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL))
        }
    } catch (e: Exception) {
        OrientedRgb.NORMAL
    }

    private fun open(context: Context, uri: Uri): InputStream =
        context.contentResolver.openInputStream(uri)
            ?: throw ImageDecodeException("Cannot open the selected image.")

    private fun javaHeapAvailable(): Long {
        val rt = Runtime.getRuntime()
        return rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())
    }

    /** Bitmap pixels are native memory on API 26+; budget against device RAM. */
    private fun nativeAvailable(context: Context): Long {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            ?: return Long.MAX_VALUE
        val mi = ActivityManager.MemoryInfo()
        am.getMemoryInfo(mi)
        return (mi.availMem - mi.threshold).coerceAtLeast(0L)
    }

    private fun memoryMessage(w: Int, h: Int) =
        "Not enough memory to analyse this $w x $h image. Close other apps and " +
        "retry, or use a lower-resolution photograph. The image is not shrunk " +
        "automatically, because that would change what the model sees."

    private fun sampleSizeFor(w: Int, h: Int, maxEdge: Int): Int {
        var s = 1
        while (maxOf(w, h) / (s * 2) >= maxEdge) s *= 2
        return s
    }

    /** Display only. The model path uses OrientedRgb's exact permutation instead. */
    private fun rotateForDisplay(src: Bitmap, orientation: Int): Bitmap {
        val m = Matrix()
        when (orientation) {
            OrientedRgb.FLIP_HORIZONTAL -> m.postScale(-1f, 1f)
            OrientedRgb.ROTATE_180 -> m.postRotate(180f)
            OrientedRgb.FLIP_VERTICAL -> m.postScale(1f, -1f)
            OrientedRgb.TRANSPOSE -> { m.postRotate(90f); m.postScale(-1f, 1f) }
            OrientedRgb.ROTATE_90 -> m.postRotate(90f)
            OrientedRgb.TRANSVERSE -> { m.postRotate(-90f); m.postScale(-1f, 1f) }
            OrientedRgb.ROTATE_270 -> m.postRotate(-90f)
            else -> return src
        }
        return Bitmap.createBitmap(src, 0, 0, src.width, src.height, m, true)
    }

    /** Display only. */
    private fun scaleForDisplay(src: Bitmap, maxEdge: Int): Bitmap {
        val longest = maxOf(src.width, src.height)
        if (longest <= maxEdge) return src
        val s = maxEdge.toDouble() / longest
        return Bitmap.createScaledBitmap(src,
            (src.width * s).toInt().coerceAtLeast(1),
            (src.height * s).toInt().coerceAtLeast(1), true)
    }
}
