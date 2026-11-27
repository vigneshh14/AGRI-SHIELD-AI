package org.agrishield.ai

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import org.agrishield.ai.ml.Classifier
import org.agrishield.ai.ml.ImageLoader
import org.agrishield.ai.preprocess.AgriShieldPreprocess
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * On-device tests. Run with `./gradlew connectedAndroidTest` with the phone
 * attached.
 *
 * The important one is decoderParity. The Phase 4 JVM parity result holds
 * *given identical input pixels*; it says nothing about whether Android's JPEG
 * decoder produces the same pixels as Pillow for the same file. JPEG decoding
 * has implementation freedom in chroma upsampling and the IDCT, so this has to
 * be measured on the device rather than assumed.
 *
 * The test does NOT assert zero difference. It measures, writes the numbers to
 * the app's external files directory, and fails only if the divergence is large
 * enough to matter. Pull the JSON with:
 *   adb pull /sdcard/Android/data/org.agrishield.ai/files/decoder_parity.json
 */
@RunWith(AndroidJUnit4::class)
class DecoderParityTest {

    private val ctx get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun modelAssetIsPresentAndAuthentic() {
        val dest = File(ctx.filesDir, Classifier.ASSET_NAME)
        if (!dest.exists()) {
            ctx.assets.open(Classifier.ASSET_NAME).use { i ->
                dest.outputStream().use { i.copyTo(it) } }
        }
        assertEquals("model in assets is not the frozen Phase 1 artifact",
            Classifier.EXPECTED_SHA256.lowercase(), Classifier.sha256(dest).lowercase())
    }

    @Test fun modelLoadsAndProducesFourLogits() {
        val c = Classifier.create(ctx)
        try {
            val px = ByteArray(96 * 96 * 3) { 128.toByte() }
            val p = c.classify(AgriShieldPreprocess.Img(96, 96, px))
            assertEquals(4, p.probabilities.size)
            val sum = p.probabilities.sum()
            assertEquals("softmax must sum to 1", 1.0f, sum, 1e-4f)
            assertTrue("latency should be positive", p.latencyMs > 0.0)
        } finally { c.close() }
    }

    /**
     * Decodes the bundled reference JPEG on-device and compares the raw RGB
     * against the values Pillow produced for the same file on the desktop.
     */
    @Test fun decoderParity() {
        val jpegBytes = ctx.assets.open("parity_reference.jpg").use { it.readBytes() }
        val expected = ctx.assets.open("parity_reference_pillow.rgb").use { it.readBytes() }

        val decodedBmp = BitmapFactory.decodeByteArray(
            jpegBytes, 0, jpegBytes.size,
            BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 })
        assertNotNull("Android could not decode parity_reference.jpg", decodedBmp)
        val bmp: Bitmap = decodedBmp!!

        val android = ImageLoader.toRgb(bmp)
        // header of the pillow dump: 8 bytes, width and height as big-endian ints
        val pw = ((expected[0].toInt() and 0xFF) shl 24) or ((expected[1].toInt() and 0xFF) shl 16) or
                 ((expected[2].toInt() and 0xFF) shl 8) or (expected[3].toInt() and 0xFF)
        val ph = ((expected[4].toInt() and 0xFF) shl 24) or ((expected[5].toInt() and 0xFF) shl 16) or
                 ((expected[6].toInt() and 0xFF) shl 8) or (expected[7].toInt() and 0xFF)
        assertEquals("decoded width differs", pw, android.w)
        assertEquals("decoded height differs", ph, android.h)

        var maxDiff = 0; var sum = 0L; var sq = 0.0; var differing = 0
        val n = android.px.size
        for (i in 0 until n) {
            val a = android.px[i].toInt() and 0xFF
            val b = expected[8 + i].toInt() and 0xFF
            val d = Math.abs(a - b)
            if (d > 0) differing++
            if (d > maxDiff) maxDiff = d
            sum += d; sq += (d * d).toDouble()
        }
        val mean = sum.toDouble() / n
        val rms = Math.sqrt(sq / n)

        // Also report the downstream effect, which is what actually matters.
        val tAndroid = AgriShieldPreprocess.preprocess(android)
        val tPillow = AgriShieldPreprocess.preprocess(
            AgriShieldPreprocess.Img(pw, ph, expected.copyOfRange(8, 8 + pw * ph * 3)))
        var tMax = 0.0f; var tSum = 0.0
        for (i in tAndroid.indices) {
            val d = Math.abs(tAndroid[i] - tPillow[i])
            if (d > tMax) tMax = d
            tSum += d.toDouble()
        }

        val json = """
            {
              "decoded_size": "${android.w}x${android.h}",
              "pixel_bytes_compared": $n,
              "pixels_differing": $differing,
              "pixel_max_abs_diff": $maxDiff,
              "pixel_mean_abs_diff": $mean,
              "pixel_rms_diff": $rms,
              "tensor_max_abs_diff": $tMax,
              "tensor_mean_abs_diff": ${tSum / tAndroid.size},
              "note": "Android BitmapFactory vs Pillow on the same JPEG. Non-zero is expected; JPEG decoding has implementation freedom."
            }
        """.trimIndent()
        File(ctx.getExternalFilesDir(null), "decoder_parity.json").writeText(json)
        println("DECODER PARITY: $json")

        // The tensor range spans about 4.4. A divergence above 0.1 would be
        // comparable to the createScaledBitmap error this project rejected, and
        // would mean the desktop reference no longer describes the device.
        assertTrue("decoder divergence propagates too far into the tensor: $tMax",
            tMax < 0.1f)
    }
}
