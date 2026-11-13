package org.agrishield.ai.preprocess

/**
 * EXIF-orientation-corrected RGB extraction, with bounded memory.
 *
 * Pure Kotlin, no Android imports, so it is compiled and tested on a desktop
 * JVM against Pillow's ImageOps.exif_transpose — the function the Phase 3
 * Python pipeline uses.
 *
 * Why this exists instead of Bitmap.createBitmap(src, ..., matrix, filter=true):
 *
 *  1. Exactness. Pillow's exif_transpose is a pure pixel permutation (flip /
 *     rotate by multiples of 90 degrees). Android's matrix path goes through
 *     Skia with filtering enabled; for axis-aligned 90-degree steps it is
 *     usually exact, but nothing documents a guarantee. Doing the permutation
 *     here makes it exact by construction, and testable.
 *  2. Memory. createBitmap allocates a second full-resolution bitmap while the
 *     first is still alive: +48 MB for a 4000x3000 photograph. Here the
 *     permutation is applied while copying pixels into the RGB array that is
 *     needed anyway, so the rotated bitmap is never created.
 *
 * Source pixels are pulled a strip of rows at a time through [RowSource], so the
 * only full-size Java-heap allocation is the RGB output itself (w*h*3 bytes),
 * which the verified resampler requires as input.
 */
object OrientedRgb {

    // EXIF Orientation tag values (TIFF 6.0 / EXIF 2.3), as used by Pillow and
    // androidx.exifinterface. Duplicated here so this file has no Android deps.
    const val NORMAL = 1
    const val FLIP_HORIZONTAL = 2
    const val ROTATE_180 = 3
    const val FLIP_VERTICAL = 4
    const val TRANSPOSE = 5
    const val ROTATE_90 = 6        // display requires 90 deg clockwise
    const val TRANSVERSE = 7
    const val ROTATE_270 = 8       // display requires 90 deg counter-clockwise

    /** Rows fetched per call; 256 rows x 4000 px x 4 B is ~4 MB. */
    const val STRIP_ROWS = 256

    /** Supplies [rows] rows of ARGB pixels starting at row [y], packed w-wide into [dst]. */
    fun interface RowSource {
        fun read(y: Int, rows: Int, dst: IntArray)
    }

    /** Unknown or out-of-range tags behave as NORMAL, matching Pillow. */
    fun normalise(orientation: Int): Int =
        if (orientation in 1..8) orientation else NORMAL

    fun swapsAxes(orientation: Int): Boolean = normalise(orientation) >= TRANSPOSE

    /** (width, height) of the upright image. */
    fun orientedSize(w: Int, h: Int, orientation: Int): Pair<Int, Int> =
        if (swapsAxes(orientation)) Pair(h, w) else Pair(w, h)

    /**
     * Fraction of the upright frame that survives Resize(109) + CenterCrop(96).
     * Computed from dimensions only — no decode needed.
     */
    fun retainedAreaFraction(uprightW: Int, uprightH: Int): Double {
        if (uprightW <= 0 || uprightH <= 0) return 0.0
        val short = minOf(uprightW, uprightH).toDouble()
        val long = maxOf(uprightW, uprightH).toDouble()
        val ns = AgriShieldPreprocess.RESIZE_SHORT
        if (short.toInt() == ns) {
            // torchvision returns the image unchanged in this case
            val s = AgriShieldPreprocess.IMG_SIZE.toDouble()
            return (s * s) / (short * long)
        }
        val nl = (ns.toDouble() * long / short).toInt()
        val s = AgriShieldPreprocess.IMG_SIZE.toDouble()
        return (s * s) / (ns.toDouble() * nl.toDouble())
    }

    /**
     * Pulls a [w] x [h] source through [src] and returns the upright image as
     * interleaved 8-bit RGB. Alpha is discarded without compositing, which is
     * what Pillow's convert("RGB") does.
     *
     * @throws IllegalArgumentException if the output would not fit in a JVM array.
     */
    fun extract(w: Int, h: Int, orientation: Int, src: RowSource,
                stripRows: Int = STRIP_ROWS): AgriShieldPreprocess.Img {
        require(w > 0 && h > 0) { "image has zero size ($w x $h)" }
        val total = w.toLong() * h.toLong() * 3L
        require(total <= Int.MAX_VALUE.toLong() - 8) {
            "a $w x $h image needs $total bytes of RGB, beyond the JVM array limit"
        }
        val o = normalise(orientation)
        val (ow, oh) = orientedSize(w, h, o)
        val out = ByteArray(total.toInt())
        val rowsPerStrip = minOf(maxOf(stripRows, 1), h)
        val strip = IntArray(w * rowsPerStrip)

        var y0 = 0
        while (y0 < h) {
            val rows = minOf(rowsPerStrip, h - y0)
            src.read(y0, rows, strip)
            for (r in 0 until rows) {
                val sy = y0 + r
                val rowBase = r * w
                for (sx in 0 until w) {
                    val dx: Int
                    val dy: Int
                    when (o) {
                        FLIP_HORIZONTAL -> { dx = w - 1 - sx; dy = sy }
                        ROTATE_180      -> { dx = w - 1 - sx; dy = h - 1 - sy }
                        FLIP_VERTICAL   -> { dx = sx;         dy = h - 1 - sy }
                        TRANSPOSE       -> { dx = sy;         dy = sx }
                        ROTATE_90       -> { dx = h - 1 - sy; dy = sx }
                        TRANSVERSE      -> { dx = h - 1 - sy; dy = w - 1 - sx }
                        ROTATE_270      -> { dx = sy;         dy = w - 1 - sx }
                        else            -> { dx = sx;         dy = sy }
                    }
                    val p = strip[rowBase + sx]
                    val di = (dy * ow + dx) * 3
                    out[di] = ((p shr 16) and 0xFF).toByte()
                    out[di + 1] = ((p shr 8) and 0xFF).toByte()
                    out[di + 2] = (p and 0xFF).toByte()
                }
            }
            y0 += rows
        }
        return AgriShieldPreprocess.Img(ow, oh, out)
    }
}
