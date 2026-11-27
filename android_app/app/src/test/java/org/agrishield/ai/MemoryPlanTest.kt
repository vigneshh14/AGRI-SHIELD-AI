package org.agrishield.ai

import org.agrishield.ai.preprocess.MemoryPlan
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pre-flight memory accounting. Figures cross-checked against a measured JVM run. */
class MemoryPlanTest {

    @Test fun twelveMegapixelPlanIsItemisedCorrectly() {
        val p = MemoryPlan.of(4000, 3000, 1)
        assertEquals(48_000_000L, p.nativeBitmapBytes)     // ARGB_8888
        assertEquals(36_000_000L, p.rgbBytes)              // RGB for the resampler
        assertEquals(4000L * 256 * 4, p.stripBytes)        // one 256-row strip
        assertEquals(145L * 3000 * 3, p.horizontalPassBytes)
        assertTrue("Java peak must include the RGB array", p.javaPeakBytes >= p.rgbBytes)
    }

    @Test fun rotatedPortraitUsesUprightDimensions() {
        val p = MemoryPlan.of(3000, 4000, 6)
        assertEquals(4000, p.uprightW)
        assertEquals(3000, p.uprightH)
    }

    @Test fun ampleBudgetIsAccepted() {
        val p = MemoryPlan.of(4000, 3000, 1)
        assertEquals(MemoryPlan.Verdict.Ok, MemoryPlan.check(p, 256_000_000L, 2_000_000_000L))
    }

    @Test fun smallHeapIsRefusedWithAReadableReason() {
        val p = MemoryPlan.of(4000, 3000, 1)
        val v = MemoryPlan.check(p, 44_000_000L, 2_000_000_000L)
        assertTrue(v is MemoryPlan.Verdict.TooLarge)
        assertTrue((v as MemoryPlan.Verdict.TooLarge).reason.contains("not shrunk automatically"))
    }

    @Test fun lowNativeMemoryIsRefused() {
        val p = MemoryPlan.of(4000, 3000, 1)
        assertTrue(MemoryPlan.check(p, 256_000_000L, 30_000_000L) is MemoryPlan.Verdict.TooLarge)
    }

    @Test fun fullResolution108MpCaptureIsRefusedOnATypicalHeap() {
        // The Infinix NOTE 30 5G main sensor is 108 MP (12000 x 9000).
        val p = MemoryPlan.of(12000, 9000, 1)
        assertEquals(324_000_000L, p.rgbBytes)
        assertTrue(MemoryPlan.check(p, 256_000_000L, 2_000_000_000L) is MemoryPlan.Verdict.TooLarge)
    }

    @Test fun requirementCoversMeasuredJvmPeaks() {
        // Measured Java-heap peaks from the Phase 4 desktop-JVM run, in bytes.
        val measured = mapOf(Pair(640, 480) to 2_300_000L, Pair(1920, 1080) to 9_500_000L,
                             Pair(4000, 3000) to 42_200_000L)
        for ((size, peak) in measured) {
            val p = MemoryPlan.of(size.first, size.second, 1)
            assertTrue("${size.first}x${size.second}: require ${p.javaRequiredBytes} < measured $peak",
                p.javaRequiredBytes >= peak)
        }
    }

    @Test fun arrayLimitOverflowIsRefused() {
        val p = MemoryPlan.of(30000, 30000, 1)
        assertTrue(MemoryPlan.check(p, Long.MAX_VALUE, Long.MAX_VALUE) is MemoryPlan.Verdict.TooLarge)
    }
}
