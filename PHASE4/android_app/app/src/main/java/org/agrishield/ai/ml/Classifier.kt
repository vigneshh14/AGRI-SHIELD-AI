package org.agrishield.ai.ml

import android.content.Context
import org.agrishield.ai.preprocess.AgriShieldPreprocess
import org.pytorch.executorch.EValue
import org.pytorch.executorch.Module
import org.pytorch.executorch.Tensor
import java.io.File
import java.security.MessageDigest

/**
 * Loads agrishield_tomato4.pte and runs it with the ExecuTorch XNNPACK backend.
 *
 * The .pte is the frozen Phase 1 artifact. Its SHA-256 is checked before
 * Module.load(), for the same reason the Phase 2 and Phase 3 runners check it:
 * a number produced by some other file is worthless, and a silent substitution
 * is worse than a crash.
 *
 * Thread safety and lifetime are delegated to [InferenceGuard]:
 *  - forward() calls are serialised;
 *  - close() never frees the native module underneath a running forward();
 *  - the module is destroyed exactly once.
 *
 * ExecuTorch API used — each call checked against the published 1.5.x Java API:
 *   Module.load(String)                     static, returns Module
 *   Tensor.fromBlob(float[], long[])        static, returns Tensor
 *   EValue.from(Tensor)                     static, returns EValue
 *   Module.forward(EValue...)               returns EValue[]
 *   EValue.isTensor (property), EValue.toTensor()
 *   Tensor.dataAsFloatArray (property; Kotlin API since 1.5)
 *   Module.destroy()
 */
class Classifier private constructor(private val module: Module) {

    /** Plain class, not a data class: data classes compare FloatArray by reference. */
    class Prediction(
        val classIndex: Int,
        val label: String,
        val probabilities: FloatArray,
        val logits: FloatArray,
        /** forward() only — excludes decode and preprocessing. */
        val latencyMs: Double,
        /** Preprocessing (resize, crop, normalise) on the device. */
        val preprocessMs: Double
    ) {
        val confidence: Float get() = probabilities[classIndex]
        val runnerUp: Int
            get() = probabilities.indices.filter { it != classIndex }
                .maxByOrNull { probabilities[it] } ?: classIndex
        val margin: Float get() = confidence - probabilities[runnerUp]
    }

    class ModelException(message: String, cause: Throwable? = null) :
        Exception(message, cause)

    private val guard = InferenceGuard { module.destroy() }

    val isClosed: Boolean get() = guard.isClosed

    /**
     * @throws InferenceGuard.ClosedException if [close] has been called
     * @throws ModelException on any model or output-shape failure
     */
    fun classify(img: AgriShieldPreprocess.Img): Prediction {
        // Preprocessing touches no native state, so it runs outside the guard
        // and does not hold up a concurrent close().
        val p0 = System.nanoTime()
        val input = AgriShieldPreprocess.preprocess(img)
        val preprocessMs = (System.nanoTime() - p0) / 1_000_000.0

        val expected = 3 * AgriShieldPreprocess.IMG_SIZE * AgriShieldPreprocess.IMG_SIZE
        if (input.size != expected) {
            throw ModelException("preprocessing produced ${input.size} floats, expected $expected")
        }
        val shape = longArrayOf(1, 3,
            AgriShieldPreprocess.IMG_SIZE.toLong(), AgriShieldPreprocess.IMG_SIZE.toLong())

        return guard.run {
            val tensor = Tensor.fromBlob(input, shape)
            val t0 = System.nanoTime()
            val out = try {
                module.forward(EValue.from(tensor))
            } catch (t: Throwable) {
                throw ModelException("ExecuTorch forward() failed: ${t.message}", t)
            }
            val latencyMs = (System.nanoTime() - t0) / 1_000_000.0

            if (out.isEmpty() || !out[0].isTensor) {
                throw ModelException("Model returned no tensor output.")
            }
            val logits = out[0].toTensor().dataAsFloatArray
            if (logits.size != AgriShieldPreprocess.CLASSES.size) {
                throw ModelException(
                    "Model returned ${logits.size} logits, expected " +
                    "${AgriShieldPreprocess.CLASSES.size}. This is not the expected 4-class model.")
            }
            val probs = softmax(logits)
            var best = 0
            for (i in probs.indices) if (probs[i] > probs[best]) best = i
            Prediction(best, AgriShieldPreprocess.CLASSES[best], probs, logits,
                latencyMs, preprocessMs)
        }
    }

    /** Non-blocking and idempotent. Defers destruction if forward() is running. */
    fun close() = guard.close()

    companion object {
        const val ASSET_NAME = "agrishield_tomato4.pte"

        /** SHA-256 of the frozen Phase 1 artifact. */
        const val EXPECTED_SHA256 =
            "f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b"

        /**
         * Copies the model out of assets (ExecuTorch needs a real file path),
         * verifies its hash, then loads it. Blocking: call off the main thread.
         */
        fun create(context: Context, verifyHash: Boolean = true): Classifier {
            val app = context.applicationContext
            val dest = File(app.filesDir, ASSET_NAME)

            if (!dest.exists() || dest.length() == 0L) copyAssetAtomically(app, dest)

            if (verifyHash) {
                val actual = sha256(dest)
                if (!actual.equals(EXPECTED_SHA256, ignoreCase = true)) {
                    // A stale or tampered copy: delete it so the next launch recopies
                    // from the APK, which is itself the thing that must be checked.
                    dest.delete()
                    throw ModelException(
                        "Model hash mismatch — refusing to run.\n" +
                        "expected $EXPECTED_SHA256\ngot      $actual")
                }
            }

            val module = try {
                Module.load(dest.absolutePath)
            } catch (t: Throwable) {
                throw ModelException("ExecuTorch could not load the model: ${t.message}", t)
            }
            return Classifier(module)
        }

        /**
         * Copy to a temporary file, then rename. If the process dies mid-copy, a
         * partial file is never left under the real name — previously that would
         * have failed the hash check on every launch until the user cleared data.
         */
        private fun copyAssetAtomically(context: Context, dest: File) {
            val tmp = File(dest.parentFile, "$ASSET_NAME.partial")
            try {
                tmp.delete()
                context.assets.open(ASSET_NAME).use { input ->
                    tmp.outputStream().use { input.copyTo(it) }
                }
                if (!tmp.renameTo(dest)) {
                    throw ModelException("Could not move the model into place at ${dest.path}.")
                }
            } catch (e: ModelException) {
                tmp.delete(); throw e
            } catch (e: Exception) {
                tmp.delete()
                throw ModelException(
                    "Could not copy $ASSET_NAME out of the app package. Was the model " +
                    "copied into app/src/main/assets/ before building? See BUILD_INSTRUCTIONS.md §2.", e)
            }
        }

        fun sha256(f: File): String {
            val md = MessageDigest.getInstance("SHA-256")
            f.inputStream().use { ins ->
                val buf = ByteArray(1 shl 16)
                while (true) {
                    val n = ins.read(buf)
                    if (n <= 0) break
                    md.update(buf, 0, n)
                }
            }
            return md.digest().joinToString("") { "%02x".format(it) }
        }

        /** Max-subtracted softmax in double precision, matching the Phase 2/3 runner. */
        fun softmax(logits: FloatArray): FloatArray {
            var mx = Float.NEGATIVE_INFINITY
            for (v in logits) if (v > mx) mx = v
            var sum = 0.0
            val e = DoubleArray(logits.size)
            for (i in logits.indices) { e[i] = Math.exp((logits[i] - mx).toDouble()); sum += e[i] }
            return FloatArray(logits.size) { (e[it] / sum).toFloat() }
        }
    }
}
