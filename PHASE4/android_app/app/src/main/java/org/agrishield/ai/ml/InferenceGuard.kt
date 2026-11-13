package org.agrishield.ai.ml

import java.util.concurrent.locks.ReentrantLock

/**
 * Serialises inference and makes native-resource release safe.
 *
 * Guarantees:
 *  1. The resource is NEVER released while a [run] block is executing. A
 *     coroutine or thread being cancelled does not interrupt a blocking JNI
 *     call, so without this an activity/ViewModel teardown could free the
 *     native ExecuTorch module underneath a running forward() — a
 *     use-after-free in native code, which crashes rather than throws.
 *  2. The resource is released EXACTLY once, however many times [close] is
 *     called and from however many threads.
 *  3. [close] never blocks. If inference is in flight, release is deferred and
 *     performed by the thread that finishes the last in-flight [run]. This
 *     matters because close() is typically called from the main thread.
 *  4. After [close], [run] refuses new work with [ClosedException].
 *  5. [run] blocks are serialised: the ExecuTorch Java Module does not document
 *     thread safety for concurrent forward() calls, so none are made.
 *
 * Pure Kotlin (java.util.concurrent only), so it is tested on a desktop JVM.
 */
class InferenceGuard(private val release: () -> Unit) {

    class ClosedException : IllegalStateException("model has been released")

    private val stateLock = Any()
    private val execLock = ReentrantLock()

    private var inFlight = 0
    private var closeRequested = false
    private var released = false

    val isReleased: Boolean get() = synchronized(stateLock) { released }
    val isClosed: Boolean get() = synchronized(stateLock) { closeRequested || released }

    fun <T> run(block: () -> T): T {
        synchronized(stateLock) {
            if (closeRequested || released) throw ClosedException()
            inFlight++
        }
        try {
            execLock.lock()
            try {
                return block()
            } finally {
                execLock.unlock()
            }
        } finally {
            val releaseNow = synchronized(stateLock) {
                inFlight--
                closeRequested && inFlight == 0 && !released
            }
            if (releaseNow) releaseOnce()
        }
    }

    /** Idempotent and non-blocking. */
    fun close() {
        val releaseNow = synchronized(stateLock) {
            if (released || closeRequested) return
            closeRequested = true
            inFlight == 0
        }
        if (releaseNow) releaseOnce()
    }

    private fun releaseOnce() {
        synchronized(stateLock) {
            if (released) return
            released = true
        }
        // Outside the lock: release() may be slow, and must not hold up run().
        try { release() } catch (_: Throwable) { /* best effort; already marked */ }
    }
}
