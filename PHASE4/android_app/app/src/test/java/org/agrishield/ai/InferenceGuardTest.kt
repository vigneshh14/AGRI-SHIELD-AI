package org.agrishield.ai

import org.agrishield.ai.ml.InferenceGuard
import org.agrishield.ai.ml.OwnedResource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/**
 * Lifetime of the native ExecuTorch module. Freeing it during forward() is a
 * native use-after-free — a crash, not an exception — so these are real-thread
 * tests, not mocks of the timing.
 */
class InferenceGuardTest {

    @Test(timeout = 10_000) fun closeDuringInferenceDefersReleaseAndDoesNotBlock() {
        val released = AtomicInteger(0)
        val g = InferenceGuard { released.incrementAndGet() }
        val started = CountDownLatch(1)
        val t = Thread { g.run { started.countDown(); Thread.sleep(300) } }
        t.start(); started.await()
        val t0 = System.nanoTime(); g.close()
        assertTrue("close() blocked", (System.nanoTime() - t0) < 50_000_000L)
        assertEquals("released during forward()", 0, released.get())
        t.join()
        assertEquals(1, released.get())
    }

    @Test(expected = InferenceGuard.ClosedException::class)
    fun runAfterCloseIsRefused() {
        val g = InferenceGuard { }
        g.close(); g.run { }
    }

    @Test(timeout = 10_000) fun concurrentClosesReleaseExactlyOnce() {
        val released = AtomicInteger(0)
        val g = InferenceGuard { released.incrementAndGet() }
        val pool = Executors.newFixedThreadPool(8); val go = CountDownLatch(1)
        repeat(400) { pool.submit { go.await(); g.close() } }
        go.countDown(); pool.shutdown(); pool.awaitTermination(5, TimeUnit.SECONDS)
        assertEquals(1, released.get())
    }

    @Test(timeout = 20_000) fun forwardCallsAreSerialised() {
        val g = InferenceGuard { }
        val inside = AtomicInteger(0); val maxInside = AtomicInteger(0)
        val pool = Executors.newFixedThreadPool(8)
        repeat(100) { pool.submit { g.run {
            maxInside.accumulateAndGet(inside.incrementAndGet()) { a, b -> maxOf(a, b) }
            Thread.sleep(1); inside.decrementAndGet() } } }
        pool.shutdown(); pool.awaitTermination(15, TimeUnit.SECONDS)
        assertEquals(1, maxInside.get())
    }

    @Test(timeout = 30_000) fun randomisedInterleavingsNeverReleaseMidForward() {
        repeat(200) { iter ->
            val inBlock = AtomicInteger(0); val bad = AtomicBoolean(false); val n = AtomicInteger(0)
            val g = InferenceGuard { if (inBlock.get() > 0) bad.set(true); n.incrementAndGet() }
            val pool = Executors.newFixedThreadPool(6); val go = CountDownLatch(1)
            repeat(12) { k -> pool.submit {
                go.await()
                if (k % 4 == 0) g.close() else try {
                    g.run { inBlock.incrementAndGet(); Thread.sleep(0, 50_000 * (iter % 7)); inBlock.decrementAndGet() }
                } catch (_: InferenceGuard.ClosedException) { }
            } }
            go.countDown(); pool.shutdown(); pool.awaitTermination(5, TimeUnit.SECONDS)
            assertFalse("released during forward() at iteration $iter", bad.get())
            assertEquals("release count at iteration $iter", 1, n.get())
        }
    }

    @Test fun exceptionInsideRunDoesNotLeakInFlightCount() {
        val released = AtomicInteger(0)
        val g = InferenceGuard { released.incrementAndGet() }
        try { g.run { throw RuntimeException("forward failed") } } catch (_: RuntimeException) { }
        g.close()
        assertEquals(1, released.get())
    }

    // ---- OwnedResource: the model arriving after the screen has gone

    @Test fun lateArrivalAfterCloseIsReleasedImmediately() {
        val released = AtomicInteger(0)
        val slot = OwnedResource<String> { released.incrementAndGet() }
        slot.close()                                  // onCleared() during model load
        assertFalse(slot.adopt("module"))             // load completes afterwards
        assertEquals("late module leaked", 1, released.get())
        assertNull(slot.get())
    }

    @Test fun normalPathReleasesOnceOnClose() {
        val released = AtomicInteger(0)
        val slot = OwnedResource<String> { released.incrementAndGet() }
        assertTrue(slot.adopt("module"))
        assertEquals("module", slot.get())
        slot.close(); slot.close()
        assertEquals(1, released.get())
    }

    @Test(timeout = 20_000) fun raceBetweenLoadAndClearNeverLeaksOrDoubleReleases() {
        repeat(500) {
            val released = AtomicInteger(0)
            val slot = OwnedResource<Any> { released.incrementAndGet() }
            val go = CountDownLatch(1)
            val a = Thread { go.await(); slot.adopt(Any()) }
            val b = Thread { go.await(); slot.close() }
            a.start(); b.start(); go.countDown(); a.join(); b.join()
            assertEquals(1, released.get())
        }
    }
}
