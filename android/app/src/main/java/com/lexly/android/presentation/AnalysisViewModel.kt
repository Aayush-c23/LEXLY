package com.lexly.android.presentation

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lexly.android.domain.model.AnalysisResult
import com.lexly.android.domain.repository.LexlyRepository
import com.lexly.android.util.PiiScrubber
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

@HiltViewModel
class AnalysisViewModel @Inject constructor(
    private val repository: LexlyRepository,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    companion object {
        private const val KEY_SESSION_ID = "saved_session_id"
        private const val KEY_CURRENT_STEP = "saved_current_step"
        private const val KEY_SCENARIO_TEXT = "saved_scenario_text"
        private const val KEY_INCIDENT_DATE = "saved_incident_date"
        private const val KEY_LOCALE = "saved_locale"
        private const val KEY_HAS_ACCEPTED_CONSENT = "saved_has_accepted_consent"
    }

    private val _uiState = MutableStateFlow<AnalysisUiState>(
        AnalysisUiState.InputState(
            text = savedStateHandle[KEY_SCENARIO_TEXT] ?: "",
            incidentDate = savedStateHandle[KEY_INCIDENT_DATE] ?: LocalDate.now().toString(),
            isValid = (savedStateHandle[KEY_SCENARIO_TEXT] ?: "").length in 20..2000,
            hasAcceptedConsent = savedStateHandle[KEY_HAS_ACCEPTED_CONSENT] ?: false,
            locale = savedStateHandle[KEY_LOCALE] ?: "en"
        )
    )
    val uiState: StateFlow<AnalysisUiState> = _uiState.asStateFlow()

    fun processIntent(intent: AnalysisUiIntent) {
        when (intent) {
            is AnalysisUiIntent.UpdateScenarioText -> onUpdateScenarioText(intent.text)
            is AnalysisUiIntent.UpdateIncidentDate -> onUpdateIncidentDate(intent.date)
            is AnalysisUiIntent.SubmitScenario -> onSubmitScenario()
            is AnalysisUiIntent.AnswerQuestion -> onAnswerQuestion(intent.answer)
            is AnalysisUiIntent.UndoStep -> onUndoStep()
            is AnalysisUiIntent.ChangeLocale -> onChangeLocale(intent.locale)
            is AnalysisUiIntent.ResetSession -> onResetSession()
            is AnalysisUiIntent.RetryLastAction -> onRetryLastAction()
            is AnalysisUiIntent.AcceptConsent -> onAcceptConsent()
            is AnalysisUiIntent.DismissConsentDialog -> onDismissConsentDialog()
        }
    }

    private fun onUpdateScenarioText(text: String) {
        savedStateHandle[KEY_SCENARIO_TEXT] = text
        _uiState.update { current ->
            if (current is AnalysisUiState.InputState) {
                current.copy(
                    text = text,
                    isValid = text.trim().length in 20..2000,
                    errorMessage = null
                )
            } else current
        }
    }

    private fun onUpdateIncidentDate(date: String) {
        savedStateHandle[KEY_INCIDENT_DATE] = date
        _uiState.update { current ->
            if (current is AnalysisUiState.InputState) {
                current.copy(incidentDate = date)
            } else current
        }
    }

    private fun onChangeLocale(locale: String) {
        savedStateHandle[KEY_LOCALE] = locale
        _uiState.update { current ->
            when (current) {
                is AnalysisUiState.InputState -> current.copy(locale = locale)
                is AnalysisUiState.InquiryState -> current.copy(locale = locale)
                is AnalysisUiState.CompletedState -> current.copy(locale = locale)
                is AnalysisUiState.EmergencyState -> current.copy(locale = locale)
                is AnalysisUiState.ErrorState -> current.copy(locale = locale)
            }
        }
    }

    private fun onSubmitScenario() {
        val currentState = _uiState.value as? AnalysisUiState.InputState ?: return
        if (!currentState.isValid) return

        if (!currentState.hasAcceptedConsent) {
            _uiState.update { currentState.copy(showConsentDialog = true) }
            return
        }

        dispatchScenarioSubmission(currentState)
    }

    private fun onAcceptConsent() {
        val currentState = _uiState.value as? AnalysisUiState.InputState ?: return
        savedStateHandle[KEY_HAS_ACCEPTED_CONSENT] = true
        val updatedState = currentState.copy(hasAcceptedConsent = true, showConsentDialog = false)
        _uiState.update { updatedState }
        if (updatedState.isValid) {
            dispatchScenarioSubmission(updatedState)
        }
    }

    private fun onDismissConsentDialog() {
        _uiState.update { current ->
            if (current is AnalysisUiState.InputState) {
                current.copy(showConsentDialog = false)
            } else current
        }
    }

    private fun dispatchScenarioSubmission(state: AnalysisUiState.InputState) {
        _uiState.update { state.copy(isLoading = true, errorMessage = null) }

        viewModelScope.launch {
            // DPDP Act 2023: Redact sensitive PII before wire transmission
            val scrubbedScenario = PiiScrubber.scrub(state.text)

            val result = repository.analyzeScenario(
                scenario = scrubbedScenario,
                incidentDate = state.incidentDate.ifBlank { null },
                locale = state.locale
            )

            result.fold(
                onSuccess = { analysisResult ->
                    handleAnalysisResult(analysisResult, state.locale)
                },
                onFailure = { error ->
                    _uiState.update {
                        AnalysisUiState.ErrorState(
                            message = error.localizedMessage ?: "Failed to analyze legal scenario",
                            canRetry = true,
                            previousState = state.copy(isLoading = false),
                            locale = state.locale
                        )
                    }
                }
            )
        }
    }

    private fun onAnswerQuestion(answer: String) {
        val currentInquiry = _uiState.value as? AnalysisUiState.InquiryState ?: return
        if (currentInquiry.isSubmitting) return

        _uiState.update { currentInquiry.copy(isSubmitting = true) }

        viewModelScope.launch {
            val result = repository.submitAnswer(
                sessionId = currentInquiry.sessionId,
                step = currentInquiry.currentStep,
                factKey = currentInquiry.question.factKey,
                answer = answer,
                locale = currentInquiry.locale
            )

            result.fold(
                onSuccess = { analysisResult ->
                    handleAnalysisResult(analysisResult, currentInquiry.locale)
                },
                onFailure = { error ->
                    _uiState.update {
                        AnalysisUiState.ErrorState(
                            message = error.localizedMessage ?: "Failed to submit answer",
                            canRetry = true,
                            previousState = currentInquiry.copy(isSubmitting = false),
                            locale = currentInquiry.locale
                        )
                    }
                }
            )
        }
    }

    private fun onUndoStep() {
        val currentInquiry = _uiState.value as? AnalysisUiState.InquiryState ?: return
        if (currentInquiry.currentStep <= 1 || currentInquiry.isSubmitting) return

        val targetStep = currentInquiry.currentStep - 1
        _uiState.update { currentInquiry.copy(isSubmitting = true) }

        viewModelScope.launch {
            val result = repository.undoStep(
                sessionId = currentInquiry.sessionId,
                targetStep = targetStep,
                locale = currentInquiry.locale
            )

            result.fold(
                onSuccess = { analysisResult ->
                    handleAnalysisResult(analysisResult, currentInquiry.locale)
                },
                onFailure = { error ->
                    _uiState.update {
                        AnalysisUiState.ErrorState(
                            message = error.localizedMessage ?: "Failed to undo step",
                            canRetry = true,
                            previousState = currentInquiry.copy(isSubmitting = false),
                            locale = currentInquiry.locale
                        )
                    }
                }
            )
        }
    }

    private fun onResetSession() {
        val current = _uiState.value
        val sessionId = when (current) {
            is AnalysisUiState.InquiryState -> current.sessionId
            is AnalysisUiState.CompletedState -> current.sessionId
            else -> savedStateHandle[KEY_SESSION_ID]
        }

        if (sessionId != null) {
            viewModelScope.launch {
                repository.purgeSession(sessionId)
            }
        }

        savedStateHandle.remove<String>(KEY_SESSION_ID)
        savedStateHandle.remove<Int>(KEY_CURRENT_STEP)

        _uiState.value = AnalysisUiState.InputState(
            text = savedStateHandle[KEY_SCENARIO_TEXT] ?: "",
            incidentDate = savedStateHandle[KEY_INCIDENT_DATE] ?: LocalDate.now().toString(),
            isValid = (savedStateHandle[KEY_SCENARIO_TEXT] ?: "").length in 20..2000,
            locale = savedStateHandle[KEY_LOCALE] ?: "en"
        )
    }

    private fun onRetryLastAction() {
        val errorState = _uiState.value as? AnalysisUiState.ErrorState ?: return
        val prev = errorState.previousState
        if (prev != null) {
            _uiState.value = prev
            when (prev) {
                is AnalysisUiState.InputState -> onSubmitScenario()
                is AnalysisUiState.InquiryState -> {
                    // Stay on current inquiry step ready for user input
                }
                else -> Unit
            }
        }
    }

    private fun handleAnalysisResult(result: AnalysisResult, locale: String) {
        when (result) {
            is AnalysisResult.Emergency -> {
                _uiState.value = AnalysisUiState.EmergencyState(
                    helplines = result.helplines,
                    advisory = result.advisory,
                    locale = locale
                )
            }

            is AnalysisResult.NeedsClarification -> {
                savedStateHandle[KEY_SESSION_ID] = result.sessionId
                savedStateHandle[KEY_CURRENT_STEP] = result.currentStep

                _uiState.value = AnalysisUiState.InquiryState(
                    sessionId = result.sessionId,
                    currentStep = result.currentStep,
                    maxSteps = result.maxSteps,
                    question = result.question,
                    remainingCandidates = result.remainingCandidates,
                    primaryRegime = result.primaryRegime,
                    isSubmitting = false,
                    locale = locale
                )
            }

            is AnalysisResult.Completed -> {
                savedStateHandle[KEY_SESSION_ID] = result.sessionId

                _uiState.value = AnalysisUiState.CompletedState(
                    sessionId = result.sessionId,
                    primaryRegime = result.primaryRegime,
                    primaryProvisions = result.primaryProvisions,
                    lesserOffences = result.lesserOffences,
                    auditTrail = result.auditTrail,
                    locale = locale
                )
            }
        }
    }
}

