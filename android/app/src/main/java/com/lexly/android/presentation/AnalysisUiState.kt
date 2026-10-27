package com.lexly.android.presentation

import com.lexly.android.domain.model.AuditStep
import com.lexly.android.domain.model.ClarificationQuestion
import com.lexly.android.domain.model.EmergencyContact
import com.lexly.android.domain.model.LesserOffenceMatch
import com.lexly.android.domain.model.ProvisionMatch

sealed interface AnalysisUiState {
    val locale: String

    data class InputState(
        val text: String = "",
        val incidentDate: String = "",
        val isValid: Boolean = false,
        val isLoading: Boolean = false,
        val errorMessage: String? = null,
        val showConsentDialog: Boolean = false,
        val hasAcceptedConsent: Boolean = false,
        override val locale: String = "en"
    ) : AnalysisUiState

    data class InquiryState(
        val sessionId: String,
        val currentStep: Int,
        val maxSteps: Int = 5,
        val question: ClarificationQuestion,
        val remainingCandidates: Int,
        val primaryRegime: String,
        val isSubmitting: Boolean = false,
        override val locale: String = "en"
    ) : AnalysisUiState

    data class CompletedState(
        val sessionId: String,
        val primaryRegime: String,
        val primaryProvisions: List<ProvisionMatch>,
        val lesserOffences: List<LesserOffenceMatch>,
        val auditTrail: List<AuditStep>,
        override val locale: String = "en"
    ) : AnalysisUiState

    data class EmergencyState(
        val helplines: List<EmergencyContact>,
        val advisory: String,
        override val locale: String = "en"
    ) : AnalysisUiState

    data class ErrorState(
        val message: String,
        val canRetry: Boolean = true,
        val previousState: AnalysisUiState? = null,
        override val locale: String = "en"
    ) : AnalysisUiState
}

