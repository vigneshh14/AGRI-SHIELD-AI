package org.agrishield.ai

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
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

    override fun onCleared() {
        // Cancelled scope + guarded close: a running forward() finishes first,
        // then the native module is destroyed exactly once.
        model.close()
        super.onCleared()
    }
}
