package org.agrishield.ai

import org.agrishield.ai.preprocess.AgriShieldPreprocess
import org.agrishield.ai.preprocess.OrientedRgb
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/**
 * EXIF orientation must reproduce Pillow's ImageOps.exif_transpose exactly —
 * the function the Phase 3 reference pipeline applies.
 *
 * Expected permutations below were produced BY PILLOW (13.0.0) on a 3x2 image
 * whose pixel k has red = k, then pasted in. They are not derived from the
 * formulas under test, which would make the test circular.
 */
class OrientedRgbTest {

    private val pillow = mapOf(
        1 to Triple(3, 2, intArrayOf(0, 1, 2, 3, 4, 5)),
        2 to Triple(3, 2, intArrayOf(2, 1, 0, 5, 4, 3)),
        3 to Triple(3, 2, intArrayOf(5, 4, 3, 2, 1, 0)),
        4 to Triple(3, 2, intArrayOf(3, 4, 5, 0, 1, 2)),
        5 to Triple(2, 3, intArrayOf(0, 3, 1, 4, 2, 5)),
        6 to Triple(2, 3, intArrayOf(3, 0, 4, 1, 5, 2)),
        7 to Triple(2, 3, intArrayOf(5, 2, 4, 1, 3, 0)),
        8 to Triple(2, 3, intArrayOf(2, 5, 1, 4, 0, 3))
    )

    private fun source(w: Int, h: Int): IntArray =
        IntArray(w * h) { k -> (0xFF shl 24) or (k shl 16) or (0x40 shl 8) or 0x80 }

    private fun run(w: Int, h: Int, o: Int, strip: Int): AgriShieldPreprocess.Img {
        val px = source(w, h)
        return OrientedRgb.extract(w, h, o,
            OrientedRgb.RowSource { y, rows, dst -> System.arraycopy(px, y * w, dst, 0, rows * w) },
            strip)
    }

    @Test fun allEightOrientationsMatchPillow() {
        for ((o, exp) in pillow) for (strip in intArrayOf(1, 2, 256)) {
            val img = run(3, 2, o, strip)
            assertEquals("orientation $o width", exp.first, img.w)
            assertEquals("orientation $o height", exp.second, img.h)
            val reds = IntArray(img.w * img.h) { img.px[it * 3].toInt() and 0xFF }
            assertArrayEquals("orientation $o, strip $strip", exp.third, reds)
        }
    }

    @Test fun greenAndBlueSurviveUnchanged_alphaDropped() {
        val img = run(3, 2, 6, 256)
        for (i in 0 until img.w * img.h) {
            assertEquals(0x40, img.px[i * 3 + 1].toInt() and 0xFF)
            assertEquals(0x80, img.px[i * 3 + 2].toInt() and 0xFF)
        }
    }

    @Test fun unknownOrientationTreatedAsNormal_likePillow() {
        assertEquals(OrientedRgb.NORMAL, OrientedRgb.normalise(0))
        assertEquals(OrientedRgb.NORMAL, OrientedRgb.normalise(9))
        assertEquals(OrientedRgb.NORMAL, OrientedRgb.normalise(-1))
    }

    @Test fun orientationsFiveToEightSwapAxes() {
        for (o in 1..4) assertEquals(Pair(4000, 3000), OrientedRgb.orientedSize(4000, 3000, o))
        for (o in 5..8) assertEquals(Pair(3000, 4000), OrientedRgb.orientedSize(4000, 3000, o))
    }

    @Test fun retainedAreaMatchesTorchvision() {
        // Values from torchvision Resize(109) itself:
        //   256x256   -> 109x109 : 9216/11881 = 0.7757
        //   4000x3000 -> 145x109 : 9216/15805 = 0.5831
        //   1920x1080 -> 193x109 : 9216/21037 = 0.4381  (109*16/9 = 193.78, truncated)
        // An earlier hand calculation used rounding where torchvision truncates;
        // this test caught the difference.
        assertEquals(0.7757, OrientedRgb.retainedAreaFraction(256, 256), 0.0001)
        assertEquals(0.5831, OrientedRgb.retainedAreaFraction(4000, 3000), 0.0001)
        assertEquals(0.4381, OrientedRgb.retainedAreaFraction(1920, 1080), 0.0001)
        assertEquals(0.4381, OrientedRgb.retainedAreaFraction(4000, 2250), 0.0001)
    }

    @Test fun refusesImagesBeyondTheArrayLimitWithoutAllocating() {
        try {
            OrientedRgb.extract(30000, 30000, 1, OrientedRgb.RowSource { _, _, _ -> })
            fail("expected IllegalArgumentException")
        } catch (e: IllegalArgumentException) {
            assertTrue(e.message!!.contains("array limit"))
        }
    }
}
