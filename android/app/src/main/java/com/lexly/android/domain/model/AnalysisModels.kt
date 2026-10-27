package com.lexly.android.domain.model

data class ProvisionMatch(
    val provisionId: Int,
    val sectionNumber: String,
    val actName: String,
    val primaryCitation: String,
    val crossReferenceCitation: String,
    val title: String,
    val plainSummary: String,
    val punishment: String,
    val isCognizable: Boolean,
    val isBailable: Boolean,
    val compoundableType: String,
    val triableBy: String,
    val posteriorProbability: Double,
    val matchedFacts: Map<String, String>
)

data class LesserOffenceMatch(
    val provisionId: Int,
    val sectionNumber: String,
    val title: String,
    val relationType: String,
    val punishment: String,
    val isCognizable: Boolean,
    val isBailable: Boolean
)

data class ClarificationQuestion(
    val factKey: String,
    val questionText: String,
    val observableProxyHint: String?,
    val category: String,
    val informationGainBits: Double
)

data class EmergencyContact(
    val title: String,
    val number: String,
    val description: String
)

data class AuditStep(
    val step: Int,
    val action: String,
    val factKey: String? = null,
    val answer: String? = null,
    val entropy: Double? = null,
    val maxProbability: Double? = null
)

sealed interface AnalysisResult {
    data class Completed(
        val sessionId: String,
        val primaryRegime: String,
        val primaryProvisions: List<ProvisionMatch>,
        val lesserOffences: List<LesserOffenceMatch>,
        val auditTrail: List<AuditStep>
    ) : AnalysisResult

    data class NeedsClarification(
        val sessionId: String,
        val currentStep: Int,
        val maxSteps: Int = 5,
        val remainingCandidates: Int,
        val question: ClarificationQuestion,
        val primaryRegime: String
    ) : AnalysisResult

    data class Emergency(
        val helplines: List<EmergencyContact>,
        val advisory: String
    ) : AnalysisResult
}

