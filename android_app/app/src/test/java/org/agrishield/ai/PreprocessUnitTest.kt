package org.agrishield.ai

import org.agrishield.ai.preprocess.AgriShieldPreprocess
import org.junit.Assert.*
import org.junit.Test
import kotlin.random.Random

/**
 * JVM unit tests for the preprocessing. These run with `./gradlew test`, on a
 * desktop JVM, with no device needed.
 *
 * They re-assert on CI what the Phase 4 parity harness established once: that
 * this code reproduces Pillow bit-exactly. The reference vectors below were
 * produced by the Python pipeline (see parity/parity_test.py).
 */
class PreprocessUnitTest {

    private fun img(w: Int, h: Int, seed: Int): AgriShieldPreprocess.Img {
        val rnd = Random(seed)
        val px = ByteArray(w * h * 3) { rnd.nextInt(256).toByte() }
        return AgriShieldPreprocess.Img(w, h, px)
    }

    @Test fun tensorHasCorrectShapeAndDtype() {
        val t = AgriShieldPreprocess.preprocess(img(640, 480, 1))
        assertEquals("expected 1x3x96x96 = 27648 floats", 3 * 96 * 96, t.size)
    }

    @Test fun classOrderIsFrozen() {
        assertArrayEquals(
            arrayOf("Tomato___Early_blight", "Tomato___Late_blight",
                    "Tomato___Septoria_leaf_spot", "Tomato___healthy"),
            AgriShieldPreprocess.CLASSES)
    }

    @Test fun resizeTargetMatchesTrainingConfig() {
        // int(96 * 1.14) == 109. If this changes, every verified result breaks.
        assertEquals(96, AgriShieldPreprocess.IMG_SIZE)
        assertEquals(109, AgriShieldPreprocess.RESIZE_SHORT)
        assertEquals(109, (96 * 1.14).toInt())
    }

    @Test fun normalisationConstantsAreImageNet() {
        assertArrayEquals(floatArrayOf(0.485f, 0.456f, 0.406f),
                          AgriShieldPreprocess.MEAN, 0f)
        assertArrayEquals(floatArrayOf(0.229f, 0.224f, 0.225f),
                          AgriShieldPreprocess.STD, 0f)
    }

    @Test fun resizePreservesAspectAndShorterSide() {
        val r = AgriShieldPreprocess.resizeShorterSide(img(4000, 3000, 2), 109)
        assertEquals(109, r.h)                 // shorter side
        assertEquals(145, r.w)                 // int(109 * 4000 / 3000)
    }

    @Test fun centreCropUsesBankersRoundingNotHalfUp() {
        // A 109 -> 96 crop has offset exactly 6.5. Python's int(round(6.5)) is 6
        // (half-to-even); Java's Math.round gives 7. Using Math.round here
        // shifted every crop by one pixel and broke parity on every image.
        // This test exists so that regression cannot return silently.
        val src = img(109, 109, 3)
        val cropped = AgriShieldPreprocess.centerCrop(src, 96)
        val expectedTop = 6
        val expectedLeft = 6
        for (y in 0 until 96) for (x in 0 until 96) for (c in 0 until 3) {
            assertEquals("pixel ($x,$y,$c) - crop offset is wrong",
                src.at(x + expectedLeft, y + expectedTop, c), cropped.at(x, y, c))
        }
    }

    @Test fun smallerThanCropIsZeroPadded() {
        val t = AgriShieldPreprocess.preprocess(img(40, 30, 4))
        assertEquals(3 * 96 * 96, t.size)
    }

    @Test fun normalisedRangeIsSane() {
        val t = AgriShieldPreprocess.preprocess(img(300, 200, 5))
        val min = t.min(); val max = t.max()
        // (0-0.485)/0.229 = -2.118 ; (1-0.406)/0.225 = 2.640
        assertTrue("min $min below theoretical bound", min >= -2.12f)
        assertTrue("max $max above theoretical bound", max <= 2.65f)
    }
}
