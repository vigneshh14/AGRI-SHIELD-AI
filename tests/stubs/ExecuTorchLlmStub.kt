// JVM-only stand-in for executorch-android's LLM classes, with the exact
// signatures of v1.6.0 (extension/android/.../extension/llm/LlmModule.kt,
// LlmCallback.kt). Used only to compile and test the engine off-device.
package org.pytorch.executorch.extension.llm

interface LlmCallback {
    fun onResult(result: String)
    fun onStats(stats: String) {}
    fun onError(errorCode: Int, message: String) {}
}

class LlmModule(modulePath: String, tokenizerPath: String, temperature: Float) : java.io.Closeable {
    companion object {
        /** Test hook: tokens the fake model will emit. */
        @JvmStatic var script: List<String> = listOf("ok")
        @JvmStatic var lastPrompt: String? = null
        @JvmStatic var lastSeqLen: Int = -1
        @JvmStatic var lastEcho: Boolean = true
        @JvmStatic var resetCalls = 0
    }
    fun generate(prompt: String, seqLen: Int, llmCallback: LlmCallback, echo: Boolean) {
        lastPrompt = prompt; lastSeqLen = seqLen; lastEcho = echo
        script.forEach { llmCallback.onResult(it) }
        llmCallback.onStats("{\"generated_tokens\":${script.size}}")
    }
    fun stop() {}
    fun resetNative() { resetCalls++ }
    override fun close() = resetNative()
}
