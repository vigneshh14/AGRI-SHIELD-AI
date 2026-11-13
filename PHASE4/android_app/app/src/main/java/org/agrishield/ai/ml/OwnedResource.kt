package org.agrishield.ai.ml

/**
 * Holds at most one closeable resource and guarantees it is released exactly
 * once, including when ownership arrives AFTER the owner has been closed.
 *
 * The case this exists for: a ViewModel starts loading the native model on a
 * background thread; the user leaves the screen; onCleared() runs while the
 * load is still in progress, finds nothing to close, and returns. The load then
 * completes and hands over a live native module that nobody will ever release.
 * With [adopt], that late arrival is released immediately instead of leaked.
 *
 * Pure Kotlin, tested on a desktop JVM.
 */
class OwnedResource<T : Any>(private val release: (T) -> Unit) {

    private val lock = Any()
    private var value: T? = null
    private var closed = false

    /** The held resource, or null if none or closed. */
    fun get(): T? = synchronized(lock) { if (closed) null else value }

    val isClosed: Boolean get() = synchronized(lock) { closed }

    /**
     * Takes ownership of [v]. Returns true if held. If this owner is already
     * closed, [v] is released at once and false is returned — the caller must
     * then stop using it.
     */
    fun adopt(v: T): Boolean {
        val accepted = synchronized(lock) {
            if (closed) false else {
                val previous = value
                value = v
                if (previous != null && previous !== v) {
                    // Replacing a held resource: release the old one outside the lock.
                    pendingRelease = previous
                }
                true
            }
        }
        drainPending()
        if (!accepted) safeRelease(v)
        return accepted
    }

    /** Idempotent. Releases the held resource, if any, exactly once. */
    fun close() {
        val toRelease = synchronized(lock) {
            if (closed) return
            closed = true
            value.also { value = null }
        }
        if (toRelease != null) safeRelease(toRelease)
    }

    private var pendingRelease: T? = null

    private fun drainPending() {
        val p = synchronized(lock) { pendingRelease.also { pendingRelease = null } }
        if (p != null) safeRelease(p)
    }

    private fun safeRelease(v: T) {
        try { release(v) } catch (_: Throwable) { /* best effort */ }
    }
}
