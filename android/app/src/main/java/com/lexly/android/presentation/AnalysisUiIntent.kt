package com.lexly.android.presentation

sealed interface AnalysisUiIntent {
    data class UpdateScenarioText(val text: String) : AnalysisUiIntent
    data class UpdateIncidentDate(val date: String) : AnalysisUiIntent
    data object SubmitScenario : AnalysisUiIntent
    data class AnswerQuestion(val answer: String) : AnalysisUiIntent
    data object UndoStep : AnalysisUiIntent
    data class ChangeLocale(val locale: String) : AnalysisUiIntent
    data object ResetSession : AnalysisUiIntent
    data object RetryLastAction : AnalysisUiIntent
    data object AcceptConsent : AnalysisUiIntent
    data object DismissConsentDialog : AnalysisUiIntent
}

