package org.agrishield.ai.preprocess

import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File

/**
 * AGRI-SHIELD AI — preprocessing, bit-compatible with the Python pipeline.
 *
 * Android's Bitmap.createScaledBitmap(..., filter = true) is a plain bilinear
 * sample with no pre-filtering. Pillow's BILINEAR scales its filter support by
 * the downscale factor, i.e. it antialiases. On a 4000x3000 -> 145x109 resize
 * (about 27x) the two diverge badly on textured content: measured max absolute
 * difference 0.8235 on the normalised tensor, whose full range spans ~4.4.
 *
 * Using createScaledBitmap would therefore feed the model materially different
 * numbers from the ones every verified result in this project was produced
 * with. This file instead reimplements Pillow's resampler exactly, including
 * its fixed-point integer arithmetic:
 *
 *   PRECISION_BITS = 32 - 8 - 2 = 22
 *   coefficients rounded to Int at that scale
 *   accumulator seeded with 1 shl (PRECISION_BITS - 1) for round-to-nearest
 *   output = (acc shr PRECISION_BITS), clamped to 0..255
 *   horizontal pass first, 8-bit intermediate, then vertical
 *
 * Transform reproduced (from train.py eval_tf / predict.py / external_eval.py):
 *   Resize(109) on the shorter side, aspect preserved, BILINEAR
 *   CenterCrop(96)
 *   ToTensor()      -> CHW float32 in [0,1]
 *   Normalize(ImageNet mean/std)
 */
object AgriShieldPreprocess {

    const val IMG_SIZE = 96
    const val RESIZE_SHORT = 109                 // int(96 * 1.14)
    private const val PRECISION_BITS = 32 - 8 - 2   // 22
    private const val SUPPORT = 1.0              // bilinear filter support

    val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
    val STD = floatArrayOf(0.229f, 0.224f, 0.225f)

    val CLASSES = arrayOf(
        "Tomato___Early_blight",
        "Tomato___Late_blight",
        "Tomato___Septoria_leaf_spot",
        "Tomato___healthy"
    )

    /** Interleaved 8-bit RGB image. */
    class Img(val w: Int, val h: Int, val px: ByteArray) {
        init { require(px.size == w * h * 3) { "expected ${w * h * 3} bytes, got ${px.size}" } }
        fun at(x: Int, y: Int, c: Int): Int = px[(y * w + x) * 3 + c].toInt() and 0xFF
    }

    private fun bilinearFilter(x: Double): Double {
        val a = if (x < 0) -x else x
        return if (a < 1.0) 1.0 - a else 0.0
    }

    private class Coeffs(val bounds: IntArray, val kk: IntArray, val ksize: Int)

    /**
     * Pillow ImagingPrecomputeCoeffs followed by normalize_coeffs_8bpc.
     * Integer truncation matches C's cast-toward-zero, which Kotlin's toInt() does.
     */
    private fun precomputeCoeffs(inSize: Int, outSize: Int): Coeffs {
        val scale = inSize.toDouble() / outSize.toDouble()
        val filterScale = if (scale >= 1.0) scale else 1.0
        val support = SUPPORT * filterScale
        val ksize = Math.ceil(support).toInt() * 2 + 1

        val bounds = IntArray(outSize * 2)
        val kk = IntArray(outSize * ksize)
        val fixedScale = (1 shl PRECISION_BITS).toDouble()
        val tmp = DoubleArray(ksize)

        for (xx in 0 until outSize) {
            val center = (xx + 0.5) * scale
            val ss = 1.0 / filterScale
            var xmin = (center - support + 0.5).toInt()
            if (xmin < 0) xmin = 0
            var xmax = (center + support + 0.5).toInt()
            if (xmax > inSize) xmax = inSize
            xmax -= xmin

            var ww = 0.0
            for (x in 0 until xmax) {
                val w = bilinearFilter((x + xmin - center + 0.5) * ss)
                tmp[x] = w
                ww += w
            }
            if (ww != 0.0) for (x in 0 until xmax) tmp[x] /= ww

            for (x in 0 until ksize) {
                val v = if (x < xmax) tmp[x] else 0.0
                // normalize_coeffs_8bpc
                kk[xx * ksize + x] =
                    if (v < 0) (v * fixedScale - 0.5).toInt() else (v * fixedScale + 0.5).toInt()
            }
            bounds[xx * 2] = xmin
            bounds[xx * 2 + 1] = xmax
        }
        return Coeffs(bounds, kk, ksize)
    }

    private fun clip8(v: Int): Int {
        val s = v shr PRECISION_BITS
        return if (s < 0) 0 else if (s > 255) 255 else s
    }

    private fun resampleHorizontal(src: Img, outW: Int): Img {
        val c = precomputeCoeffs(src.w, outW)
        val dst = ByteArray(outW * src.h * 3)
        val init = 1 shl (PRECISION_BITS - 1)
        for (yy in 0 until src.h) {
            for (xx in 0 until outW) {
                val xmin = c.bounds[xx * 2]
                val xmax = c.bounds[xx * 2 + 1]
                val ko = xx * c.ksize
                var a0 = init; var a1 = init; var a2 = init
                for (x in 0 until xmax) {
                    val k = c.kk[ko + x]
                    val base = (yy * src.w + (x + xmin)) * 3
                    a0 += (src.px[base].toInt() and 0xFF) * k
                    a1 += (src.px[base + 1].toInt() and 0xFF) * k
                    a2 += (src.px[base + 2].toInt() and 0xFF) * k
                }
                val o = (yy * outW + xx) * 3
                dst[o] = clip8(a0).toByte()
                dst[o + 1] = clip8(a1).toByte()
                dst[o + 2] = clip8(a2).toByte()
            }
        }
        return Img(outW, src.h, dst)
    }

    private fun resampleVertical(src: Img, outH: Int): Img {
        val c = precomputeCoeffs(src.h, outH)
        val dst = ByteArray(src.w * outH * 3)
        val init = 1 shl (PRECISION_BITS - 1)
        for (yy in 0 until outH) {
            val ymin = c.bounds[yy * 2]
            val ymax = c.bounds[yy * 2 + 1]
            val ko = yy * c.ksize
            for (xx in 0 until src.w) {
                var a0 = init; var a1 = init; var a2 = init
                for (y in 0 until ymax) {
                    val k = c.kk[ko + y]
                    val base = ((y + ymin) * src.w + xx) * 3
                    a0 += (src.px[base].toInt() and 0xFF) * k
                    a1 += (src.px[base + 1].toInt() and 0xFF) * k
                    a2 += (src.px[base + 2].toInt() and 0xFF) * k
                }
                val o = (yy * src.w + xx) * 3
                dst[o] = clip8(a0).toByte()
                dst[o + 1] = clip8(a1).toByte()
                dst[o + 2] = clip8(a2).toByte()
            }
        }
        return Img(src.w, outH, dst)
    }

    /** Pillow-equivalent resize. Horizontal then vertical, 8-bit intermediate. */
    fun pilResize(src: Img, outW: Int, outH: Int): Img {
        var cur = src
        if (outW != cur.w) cur = resampleHorizontal(cur, outW)
        if (outH != cur.h) cur = resampleVertical(cur, outH)
        return cur
    }

    /** torchvision Resize(size) with a single int: shorter side -> size. */
    fun resizeShorterSide(src: Img, size: Int): Img {
        val w = src.w; val h = src.h
        val short = if (w <= h) w else h
        if (short == size) return src
        val long = if (w <= h) h else w
        val newShort = size
        val newLong = (size.toDouble() * long / short).toInt()
        val nw = if (w <= h) newShort else newLong
        val nh = if (w <= h) newLong else newShort
        return pilResize(src, nw, nh)
    }

    /** torchvision CenterCrop. Pads with zeros if the source is smaller. */
    fun centerCrop(src: Img, size: Int): Img {
        var cur = src
        if (cur.w < size || cur.h < size) {
            val padded = ByteArray(size * size * 3)
            val offX = maxOf((size - cur.w) / 2, 0)
            val offY = maxOf((size - cur.h) / 2, 0)
            for (y in 0 until minOf(cur.h, size)) {
                for (x in 0 until minOf(cur.w, size)) {
                    val s = (y * cur.w + x) * 3
                    val d = ((y + offY) * size + (x + offX)) * 3
                    padded[d] = cur.px[s]
                    padded[d + 1] = cur.px[s + 1]
                    padded[d + 2] = cur.px[s + 2]
                }
            }
            cur = Img(size, size, padded)
        }
        // torchvision uses Python's int(round(x)), which is round-half-to-EVEN.
        // Java's Math.round is round-half-UP, and the offset here is very often
        // exactly .5 — for a 109 -> 96 crop it is 6.5 on every single image, so
        // Math.round would shift the crop by one pixel every time. Math.rint is
        // half-to-even and matches Python. This was caught by the parity test,
        // not by inspection; do not "simplify" it back to Math.round.
        val top = Math.rint((cur.h - size) / 2.0).toInt()
        val left = Math.rint((cur.w - size) / 2.0).toInt()
        val out = ByteArray(size * size * 3)
        for (y in 0 until size) {
            val s = ((y + top) * cur.w + left) * 3
            System.arraycopy(cur.px, s, out, y * size * 3, size * 3)
        }
        return Img(size, size, out)
    }

    /** ToTensor() then Normalize(): CHW float32, length 3*96*96. */
    fun toTensorNormalize(src: Img): FloatArray {
        val n = src.w * src.h
        val out = FloatArray(3 * n)
        for (c in 0 until 3) {
            val m = MEAN[c]; val s = STD[c]
            for (i in 0 until n) {
                val v = (src.px[i * 3 + c].toInt() and 0xFF) / 255.0f
                out[c * n + i] = (v - m) / s
            }
        }
        return out
    }

    /** Full pipeline on an already-decoded, already-EXIF-corrected RGB image. */
    fun preprocess(src: Img): FloatArray =
        toTensorNormalize(centerCrop(resizeShorterSide(src, RESIZE_SHORT), IMG_SIZE))

    // ------------------------------------------------------------- test CLI
    // Reads:  int32 w, int32 h, then w*h*3 bytes interleaved RGB  (big-endian ints)
    // Writes: 3*96*96 float32, big-endian, CHW
    @JvmStatic
    fun main(args: Array<String>) {
        if (args.size < 2) {
            System.err.println("usage: AgriShieldPreprocess <in.rgb> <out.f32>")
            return
        }
        DataInputStream(File(args[0]).inputStream().buffered()).use { din ->
            val w = din.readInt(); val h = din.readInt()
            val px = ByteArray(w * h * 3)
            din.readFully(px)
            val t = preprocess(Img(w, h, px))
            DataOutputStream(File(args[1]).outputStream().buffered()).use { dout ->
                for (v in t) dout.writeFloat(v)
            }
            System.err.println("ok ${w}x$h -> 1x3x96x96  (${t.size} floats)")
        }
    }
}
