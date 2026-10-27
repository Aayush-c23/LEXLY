package com.lexly.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AnalyzeRequestDto(
    @SerialName("scenario") val scenario: String,
    @SerialName("incident_date") val incidentDate: String? = null,
    @SerialName("locale") val locale: String = "en"
)

@Serializable
data class AnswerRequestDto(
    @SerialName("step") val step: Int,
    @SerialName("fact_key") val factKey: String,
    @SerialName("answer") val answer: String,
    @SerialName("locale") val locale: String = "en"
)

@Serializable
data class UndoRequestDto(
    @SerialName("target_step") val targetStep: Int,
    @SerialName("locale") val locale: String = "en"
)

@Serializable
data class ClarificationQuestionDto(
    @SerialName("fact_key") val factKey: String,
    @SerialName("question_text") val questionText: String,
    @SerialName("observable_proxy_hint") val observableProxyHint: String? = null,
    @SerialName("category") val category: String,
    @SerialName("information_gain_bits") val informationGainBits: Double
)

@Serializable
data class ProvisionResultDto(
    @SerialName("provision_id") val provisionId: Int,
    @SerialName("section_number") val sectionNumber: String,
    @SerialName("act_name") val actName: String,
    @SerialName("primary_citation") val primaryCitation: String,
    @SerialName("cross_reference_citation") val crossReferenceCitation: String,
    @SerialName("title") val title: String,
    @SerialName("plain_summary") val plainSummary: String,
    @SerialName("punishment") val punishment: String,
    @SerialName("is_cognizable") val isCognizable: Boolean,
    @SerialName("is_bailable") val isBailable: Boolean,
    @SerialName("compoundable_type") val compoundableType: String,
    @SerialName("triable_by") val triableBy: String,
    @SerialName("posterior_probability") val posteriorProbability: Double,
    @SerialName("matched_facts") val matchedFacts: Map<String, String> = emptyMap()
)

@Serializable
data class LesserOffenceResultDto(
    @SerialName("provision_id") val provisionId: Int,
    @SerialName("section_number") val sectionNumber: String,
    @SerialName("title") val title: String,
    @SerialName("relation_type") val relationType: String,
    @SerialName("punishment") val punishment: String,
    @SerialName("is_cognizable") val isCognizable: Boolean,
    @SerialName("is_bailable") val isBailable: Boolean
)

@Serializable
data class EmergencyContactDto(
    @SerialName("title") val title: String,
    @SerialName("number") val number: String,
    @SerialName("description") val description: String
)

@Serializable
data class AuditStepDto(
    @SerialName("step") val step: Int,
    @SerialName("action") val action: String,
    @SerialName("fact_key") val factKey: String? = null,
    @SerialName("answer") val answer: String? = null,
    @SerialName("entropy") val entropy: Double? = null,
    @SerialName("max_probability") val maxProbability: Double? = null
)

@Serializable
data class AnalyzeResponseDto(
    @SerialName("status") val status: String,
    @SerialName("session_id") val sessionId: String? = null,
    @SerialName("current_step") val currentStep: Int? = null,
    @SerialName("max_steps") val maxSteps: Int? = 5,
    @SerialName("primary_legal_regime") val primaryLegalRegime: String? = null,
    @SerialName("remaining_candidates_count") val remainingCandidatesCount: Int? = null,
    @SerialName("question") val question: ClarificationQuestionDto? = null,
    @SerialName("provisions") val provisions: List<ProvisionResultDto>? = null,
    @SerialName("lesser_included_offences") val lesserIncludedOffences: List<LesserOffenceResultDto>? = null,
    @SerialName("audit_trail") val auditTrail: List<AuditStepDto>? = null,
    @SerialName("helplines") val helplines: List<EmergencyContactDto>? = null,
    @SerialName("advisory") val advisory: String? = null
)

@Serializable
data class PurgeResponseDto(
    @SerialName("session_id") val sessionId: String,
    @SerialName("status") val status: String
)

