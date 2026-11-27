package org.agrishield.ai.preprocess

/**
 * Pre-flight memory accounting for the inference image pipeline.
 *
 * Pure Kotlin so it is unit-tested on a desktop JVM. Computes, from the image
 * dimensions alone (BitmapFactory's inJustDecodeBounds pass), every large
 * allocation the full-resolution pipeline will make, so the app can refuse an
 * image up front with a clear message instead of failing part-way through.
 *
 * Two memory pools matter on Android 8.0+ (API 26+; this app's minSdk is 28):
 *
 *  - NATIVE: Bitmap pixel buffers live in native memory, not the Java heap.
 *    They are bounded by device RAM and the low-memory killer, not by
 *    Runtime.maxMemory(). Budget: ActivityManager.MemoryInfo.availMem minus
 *    its own low-memory threshold.
 *  - JAVA HEAP: the RGB ByteArray, the row strip, and the resampler's
 *    intermediates. Budget: Runtime.maxMemory() minus what is already in use.
 *
 * This plan NEVER proposes downsampling. If the full-resolution image does not
 * fit, the answer is "cannot process this image", not a silently different one.
 * The model must see exactly the pixels the Python reference would see.
 */
object MemoryPlan {

    /** Headroom multiplier: allocator overhead, fragmentation, GC. */
    const val SAFETY_FACTOR = 1.25

    /**
     * Fixed headroom added on top. Measured on a desktop JVM, the pipeline used
     * 0.7-2.1 MB more Java heap than the itemised plan (object headers, float
     * temporaries, small arrays). A multiplier alone does not cover that for
     * small images: at 640x480 the plan was 1.6 MB, x1.25 = 2.0 MB, measured
     * 2.3 MB. A fixed term fixes the small end without inflating the large end.
     */
    const val FIXED_OVERHEAD_BYTES = 4_000_000L

    data class Plan(
        val sourceW: Int,
        val sourceH: Int,
        val uprightW: Int,
        val uprightH: Int,
        /** ARGB_8888 decode buffer — native memory. */
        val nativeBitmapBytes: Long,
        /** Full-resolution RGB array the verified resampler takes as input. */
        val rgbBytes: Long,
        /** One strip of source rows during RGB extraction. */
        val stripBytes: Long,
        /** Resampler horizontal-pass output (outW x uprightH x 3). */
        val horizontalPassBytes: Long,
        /** Resampler vertical-pass output plus crop and float tensor. */
        val tailBytes: Long,
        /** Fixed-point coefficient tables for both passes. */
        val coefficientBytes: Long
    ) {
        /**
         * Java-heap peak. The RGB array stays alive through the horizontal pass;
         * the strip is freed before resampling begins, so the two phases do not
         * stack.
         */
        val javaPeakBytes: Long
            get() = rgbBytes + maxOf(stripBytes, horizontalPassBytes + coefficientBytes + tailBytes)

        val nativePeakBytes: Long get() = nativeBitmapBytes

        /** What check() will actually require of the Java heap. */
        val javaRequiredBytes: Long
            get() = (javaPeakBytes * SAFETY_FACTOR).toLong() + FIXED_OVERHEAD_BYTES

        fun mb(b: Long): String = "%.1f MB".format(b / 1_000_000.0)
    }

    sealed class Verdict {
        object Ok : Verdict()
        data class TooLarge(val reason: String) : Verdict()
    }

    /** Resized dimensions for torchvision Resize(109) on the upright image. */
    private fun resized(uw: Int, uh: Int): Pair<Int, Int> {
        val ns = AgriShieldPreprocess.RESIZE_SHORT
        val short = minOf(uw, uh)
        if (short == ns) return Pair(uw, uh)
        val long = maxOf(uw, uh)
        val nl = (ns.toDouble() * long / short).toInt()
        return if (uw <= uh) Pair(ns, nl) else Pair(nl, ns)
    }

    /** ksize for Pillow's bilinear coefficients: ceil(support) * 2 + 1. */
    private fun ksize(inSize: Int, outSize: Int): Int {
        val scale = inSize.toDouble() / outSize.toDouble()
        val support = if (scale >= 1.0) scale else 1.0
        return Math.ceil(support).toInt() * 2 + 1
    }

    fun of(sourceW: Int, sourceH: Int, orientation: Int,
           stripRows: Int = OrientedRgb.STRIP_ROWS): Plan {
        require(sourceW > 0 && sourceH > 0) { "image has zero size" }
        val (uw, uh) = OrientedRgb.orientedSize(sourceW, sourceH, orientation)
        val px = sourceW.toLong() * sourceH.toLong()
        val (rw, rh) = resized(uw, uh)

        // AgriShieldPreprocess.pilResize: horizontal first (if width changes),
        // producing rw x uh, then vertical to rw x rh.
        val hPass = if (rw != uw) rw.toLong() * uh * 3 else 0L
        val vPass = rw.toLong() * rh * 3
        val crop = AgriShieldPreprocess.IMG_SIZE.toLong() * AgriShieldPreprocess.IMG_SIZE * 3
        val tensor = 3L * AgriShieldPreprocess.IMG_SIZE * AgriShieldPreprocess.IMG_SIZE * 4
        val coeffs = (rw.toLong() * ksize(uw, rw) + rh.toLong() * ksize(uh, rh)) * 4 +
                     (rw.toLong() + rh.toLong()) * 2 * 4

        return Plan(
            sourceW, sourceH, uw, uh,
            nativeBitmapBytes = px * 4,
            rgbBytes = px * 3,
            stripBytes = sourceW.toLong() * minOf(stripRows, sourceH) * 4,
            horizontalPassBytes = hPass,
            tailBytes = vPass + crop + tensor,
            coefficientBytes = coeffs
        )
    }

    /**
     * @param javaAvailableBytes Runtime.maxMemory() - (totalMemory() - freeMemory())
     * @param nativeAvailableBytes availMem - threshold from ActivityManager.MemoryInfo
     */
    fun check(plan: Plan, javaAvailableBytes: Long, nativeAvailableBytes: Long): Verdict {
        if (plan.rgbBytes > Int.MAX_VALUE.toLong() - 8) {
            return Verdict.TooLarge(
                "This image is ${plan.sourceW} x ${plan.sourceH} pixels. Its RGB data " +
                "(${plan.mb(plan.rgbBytes)}) exceeds the largest array Android can allocate.")
        }
        val needJava = (plan.javaPeakBytes * SAFETY_FACTOR).toLong() + FIXED_OVERHEAD_BYTES
        if (needJava > javaAvailableBytes) {
            return Verdict.TooLarge(
                "Not enough app memory to analyse a ${plan.sourceW} x ${plan.sourceH} image: " +
                "needs about ${plan.mb(needJava)}, ${plan.mb(javaAvailableBytes)} available. " +
                "Close other apps and retry, or use a lower-resolution photograph. " +
                "The image is not shrunk automatically, because that would change what the model sees.")
        }
        val needNative = (plan.nativePeakBytes * SAFETY_FACTOR).toLong() + FIXED_OVERHEAD_BYTES
        if (needNative > nativeAvailableBytes) {
            return Verdict.TooLarge(
                "The phone does not have enough free memory to decode a " +
                "${plan.sourceW} x ${plan.sourceH} image: needs about ${plan.mb(needNative)}, " +
                "${plan.mb(nativeAvailableBytes)} free. Close other apps and retry.")
        }
        return Verdict.Ok
    }
}
