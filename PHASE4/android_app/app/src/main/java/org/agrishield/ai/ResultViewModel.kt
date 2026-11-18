package org.agrishield.ai

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import android.util.Log
import com.agrishield.advisory.Decision
import com.agrishield.advisory.LlamaAdvisoryEngine
import java.io.File
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.agrishield.ai.ml.Classifier
import org.agrishield.ai.ml.ImageLoader
import org.agrishield.ai.ml.InferenceGuard
import org.agrishield.ai.ml.OwnedResource

/**
 * Owns the inference for one photograph and outlives configuration changes.
 *
 * Replaces the previous raw `thread { }` in ResultActivity, which:
 *  - re-ran the whole pipeline on every rotation;
 *  - posted to the activity with runOnUiThread even after it was destroyed;
 *  - could call classifier.close() from onDestroy() while forward() was still
 *    executing on the worker, freeing the native module underneath it;
 *  - never cancelled its work.
 *
 * Here:
 *  - [start] is idempotent: a rotation re-attaches to the same work and result.
 *  - The UI collects [state] with repeatOnLifecycle(STARTED), so nothing is
 *    delivered to a stopped or destroyed activity.
 *  - The classifier is held in an [OwnedResource]: if the screen is cleared
 *    while the model is still loading, the late-arriving module is released
 *    immediately instead of leaking.
 *  - The classifier's [InferenceGuard] defers native release until a running
 *    forward() returns, and releases exactly once.
 *  - viewModelScope is cancelled before onCleared(); a check between stages
 *    stops remaining work early. A forward() already inside JNI cannot be
 *    interrupted — it completes (~12 ms on this phone) and the guard makes
 *    that safe.
 */
class ResultViewModel(app: Application) : AndroidViewModel(app) {

    sealed class UiState {
        object Idle : UiState()
        data class Working(val thumbnail: Bitmap?, val stage: String) : UiState()
        class Success(
            val thumbnail: Bitmap,
            val prediction: Classifier.Prediction,
            val input: ImageLoader.InferenceInput
        ) : UiState()
        data class Failure(val thumbnail: Bitmap?, val title: String, val detail: String) : UiState()
    }

    private val _state = MutableStateFlow<UiState>(UiState.Idle)
    val state: StateFlow<UiState> = _state.asStateFlow()

    /** Llama advisory, produced after a successful classification. */
    sealed class AdvisoryState {
        object NotStarted : AdvisoryState()
        /** The .pte / tokenizer are not on the phone yet. */
        data class ModelMissing(val dir: String) : AdvisoryState()
        data class Generating(val decision: Decision, val textSoFar: String) : AdvisoryState()
        data class Done(val result: LlamaAdvisoryEngine.Result) : AdvisoryState()
        data class Failed(val decision: Decision?, val message: String) : AdvisoryState()
    }

    private val _advisory = MutableStateFlow<AdvisoryState>(AdvisoryState.NotStarted)
    val advisory: StateFlow<AdvisoryState> = _advisory.asStateFlow()

    // Owned here, not by the activity: survives rotation, closed in onCleared().
    private var llama: LlamaAdvisoryEngine? = null
    private var advisoryStarted = false          // main thread only

    private val model = OwnedResource<Classifier> { it.close() }
    private var job: Job? = null
    private var startedFor: String? = null      // main thread only

    /** Safe to call on every onCreate; only the first call for a URI does work. */
    fun start(uriString: String) {
        if (startedFor == uriString) return
        startedFor = uriString
        job?.cancel()
        job = viewModelScope.launch(Dispatchers.Default) { runPipeline(Uri.parse(uriString)) }
    }

    private suspend fun checkActive() = currentCoroutineContext().ensureActive()

    private suspend fun runPipeline(uri: Uri) {
        val ctx = getApplication<Application>()
        var thumb: Bitmap? = null
        try {
            _state.value = UiState.Working(null, "Reading photograph")
            thumb = ImageLoader.loadPreview(ctx, uri).thumbnail
            checkActive()

            _state.value = UiState.Working(thumb, "Preparing full-resolution input")
            val input = ImageLoader.loadForInference(ctx, uri)
            checkActive()

            _state.value = UiState.Working(thumb, "Loading model")
            val classifier = model.get() ?: Classifier.create(ctx).also {
                // If onCleared() ran while the model was loading, adopt() releases
                // it on the spot and we stop here.
                if (!model.adopt(it)) throw CancellationException("cleared during model load")
            }
            checkActive()

            _state.value = UiState.Working(thumb, "Running on-device inference")
            val prediction = classifier.classify(input.img)

            _state.value = UiState.Success(thumb, prediction, input)
            Log.i(TAG_ARM, "classifier label=${prediction.label} conf=${prediction.confidence} " +
                "margin=${prediction.margin} inferMs=${prediction.latencyMs} preMs=${prediction.preprocessMs}")
            kotlinx.coroutines.withContext(Dispatchers.Main) { startAdvisory(prediction) }
        } catch (e: CancellationException) {
            throw e                                   // never report cancellation as an error
        } catch (e: InferenceGuard.ClosedException) {
            // Cleared mid-pipeline; there is no screen left to report to.
        } catch (e: ImageLoader.ImageMemoryException) {
            _state.value = UiState.Failure(thumb, "Image too large for available memory", e.userMessage)
        } catch (e: ImageLoader.ImageDecodeException) {
            _state.value = UiState.Failure(thumb, "Could not read this image", e.message ?: "")
        } catch (e: Classifier.ModelException) {
            _state.value = UiState.Failure(thumb, "Could not run the model", e.message ?: "")
        } catch (e: OutOfMemoryError) {
            _state.value = UiState.Failure(thumb, "Image too large for available memory",
                "The phone ran out of memory processing this photograph. Close other apps " +
                "and retry, or use a lower-resolution image.")
        } catch (e: Exception) {
            _state.value = UiState.Failure(thumb, "Unexpected error",
                "${e.javaClass.simpleName}: ${e.message}")
        }
    }

    /**
     * Runs gate -> prompt -> Llama 3.2 1B (ExecuTorch) -> output guard.
     * The engine runs on its own single worker thread; this only wires its
     * callbacks into [advisory]. Called on the main thread, at most once.
     */
    private fun startAdvisory(p: Classifier.Prediction) {
        if (advisoryStarted) return
        advisoryStarted = true
        val dir = File(getApplication<Application>().getExternalFilesDir(null), LLAMA_DIR)
        val pte = File(dir, LLAMA_PTE)
        val tok = File(dir, LLAMA_TOKENIZER)
        if (!pte.isFile || !tok.isFile) {
            _advisory.value = AdvisoryState.ModelMissing(dir.absolutePath)
            Log.w(TAG_ARM, "llama model missing in ${dir.absolutePath}")
            return
        }
        val decision = com.agrishield.advisory.AdvisoryGate.decide(
            p.label, p.confidence.coerceIn(0f, 1f), margin = p.margin.coerceIn(0f, 1f))
        _advisory.value = AdvisoryState.Generating(decision, "")
        val engine = llama ?: LlamaAdvisoryEngine(pte, tok).also { llama = it }
        engine.advise(
            p.label, p.confidence.coerceIn(0f, 1f), p.margin.coerceIn(0f, 1f),
            onToken = { t ->
                _advisory.update { s ->
                    if (s is AdvisoryState.Generating) s.copy(textSoFar = s.textSoFar + t) else s
                }
            },
            onDone = { r ->
                _advisory.value = AdvisoryState.Done(r)
                Log.i(TAG_ARM, "llama wallMs=${r.wallMs} fromLlama=${r.fromLlama} " +
                    "decision=${r.decision::class.simpleName} violations=${r.violations} stats=${r.statsJson}")
            },
            onError = { e ->
                _advisory.value = AdvisoryState.Failed(decision, "${e.javaClass.simpleName}: ${e.message}")
                Log.e(TAG_ARM, "llama failed", e)
            },
        )
    }

    override fun onCleared() {
        // Cancelled scope + guarded close: a running forward() finishes first,
        // then the native module is destroyed exactly once.
        model.close()
        // stop() ends a running generate() early; close() then frees ~1 GB of
        // native memory on the engine's own thread (bounded wait, < ANR limit).
        llama?.close()
        llama = null
        super.onCleared()
    }

    companion object {
        /** logcat tag for every number that goes into benchmarks/results_arm.md */
        const val TAG_ARM = "AGRI_ARM"
        /** Under getExternalFilesDir(null). Filled by scripts/get_llama_model.ps1 -Push. */
        const val LLAMA_DIR = "llama"
        const val LLAMA_PTE = "llama3_2_1b_spinquant.pte"
        const val LLAMA_TOKENIZER = "tokenizer.model"
    }
}
