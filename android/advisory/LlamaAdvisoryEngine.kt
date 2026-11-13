package com.agrishield.advisory

import org.pytorch.executorch.extension.llm.LlmCallback
import org.pytorch.executorch.extension.llm.LlmModule
import java.io.Closeable
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/*
 * M5 - Llama 3.2 1B through ExecuTorch, on the phone.
 *
 * Uses only LlmModule calls whose signatures are identical from ExecuTorch
 * 0.7.0 through 1.6.0 (checked against the tagged sources on 2026-11-13):
 *   LlmModule(modulePath, tokenizerPath, temperature)
 *   generate(prompt, seqLen, callback, echo)
 *   stop(), resetNative()
 *   LlmCallback.onResult(String), LlmCallback.onStats(String)
 * Do NOT use executorch-android 0.6.x: its LlmCallback.onStats takes a float.
 *
 * All callbacks run on the worker thread. Post to the UI with runOnUiThread.
 */
class LlamaAdvisoryEngine(
    private val modelFile: File,      // e.g. filesDir/llama/llama3_2_1b.pte
    private val tokenizerFile: File,  // e.g. filesDir/llama/tokenizer.model
    private val temperature: Float = 0.2f,
    private val seqLen: Int = 768,
) : Closeable {

    data class Result(
        val decision: Decision,
        val shownText: String,
        val fromLlama: Boolean,          // false => guard rejected, fallback shown
        val violations: List<String>,
        val rawModelText: String,
        val statsJson: String?,          // ExecuTorch stats string, for [ARM] benchmarks
        val wallMs: Long,
    )

    private val worker: ExecutorService = Executors.newSingleThreadExecutor()
    @Volatile private var module: LlmModule? = null
    @Volatile private var closed = false

    private fun moduleOrLoad(): LlmModule {
        module?.let { return it }
        check(modelFile.isFile) { "Llama model missing: ${modelFile.absolutePath}" }
        check(tokenizerFile.isFile) { "Tokenizer missing: ${tokenizerFile.absolutePath}" }
        return LlmModule(modelFile.absolutePath, tokenizerFile.absolutePath, temperature)
            .also { module = it }
    }

    /**
     * Runs gate -> prompt -> Llama -> guard. [onToken] streams raw tokens for a live UI;
     * [onDone] receives the guarded result. [onError] receives any failure.
     */
    fun advise(
        topLabel: String,
        confidence: Float,
        onToken: (String) -> Unit,
        onDone: (Result) -> Unit,
        onError: (Throwable) -> Unit,
    ) {
        check(!closed) { "engine closed" }
        worker.execute {
            val t0 = System.nanoTime()
            try {
                val decision = AdvisoryGate.decide(topLabel, confidence)
                val prompt = AdvisoryGate.buildPrompt(decision)
                val sb = StringBuilder()
                var statsOut: String? = null
                val m = moduleOrLoad()
                m.generate(prompt, seqLen, object : LlmCallback {
                    override fun onResult(result: String) {
                        sb.append(result)
                        onToken(result)
                    }
                    override fun onStats(stats: String) {
                        statsOut = stats
                    }
                }, false)
                val g = AdvisoryGate.guard(sb.toString())
                val shown = if (g.accepted) g.text else AdvisoryGate.fallbackText(decision)
                onDone(
                    Result(
                        decision, shown, g.accepted, g.violations, sb.toString(), statsOut,
                        (System.nanoTime() - t0) / 1_000_000,
                    )
                )
            } catch (t: Throwable) {
                onError(t)
            }
        }
    }

    fun stop() {
        module?.stop()
    }

    override fun close() {
        if (closed) return
        closed = true
        module?.stop()
        // Free native memory on the worker thread, after any running generate() returns.
        worker.execute {
            module?.resetNative()
            module = null
        }
        worker.shutdown()
        // stop() makes a running generate() return quickly; wait (bounded, well under the
        // 5 s ANR limit) so the ~1 GB of model memory is really released when close() returns.
        worker.awaitTermination(2, java.util.concurrent.TimeUnit.SECONDS)
    }
}
