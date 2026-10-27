package com.lexly.android.data.repository

import com.lexly.android.data.remote.LexlyApiService
import com.lexly.android.data.remote.dto.AnalyzeRequestDto
import com.lexly.android.data.remote.dto.AnalyzeResponseDto
import com.lexly.android.data.remote.dto.AnswerRequestDto
import com.lexly.android.data.remote.dto.UndoRequestDto
import com.lexly.android.domain.model.AnalysisResult
import com.lexly.android.domain.model.AuditStep
import com.lexly.android.domain.model.ClarificationQuestion
import com.lexly.android.domain.model.EmergencyContact
import com.lexly.android.domain.model.LesserOffenceMatch
import com.lexly.android.domain.model.ProvisionMatch
import com.lexly.android.domain.repository.LexlyRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LexlyRepositoryImpl @Inject constructor(
    private val apiService: LexlyApiService
) : LexlyRepository {

    override suspend fun analyzeScenario(
        scenario: String,
        incidentDate: String?,
        locale: String
    ): Result<AnalysisResult> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.analyze(
                AnalyzeRequestDto(
                    scenario = scenario,
                    incidentDate = incidentDate,
                    locale = locale
                )
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(mapResponseToDomain(response.body()!!))
            } else {
                Result.failure(Exception("API Error ${response.code()}: ${response.errorBody()?.string()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun submitAnswer(
        sessionId: String,
        step: Int,
        factKey: String,
        answer: String,
        locale: String
    ): Result<AnalysisResult> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.answer(
                sessionId = sessionId,
                request = AnswerRequestDto(
                    step = step,
                    factKey = factKey,
                    answer = answer,
                    locale = locale
                )
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(mapResponseToDomain(response.body()!!))
            } else {
                Result.failure(Exception("API Error ${response.code()}: ${response.errorBody()?.string()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun undoStep(
        sessionId: String,
        targetStep: Int,
        locale: String
    ): Result<AnalysisResult> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.undo(
                sessionId = sessionId,
                request = UndoRequestDto(
                    targetStep = targetStep,
                    locale = locale
                )
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(mapResponseToDomain(response.body()!!))
            } else {
                Result.failure(Exception("API Error ${response.code()}: ${response.errorBody()?.string()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun purgeSession(sessionId: String): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.deleteSession(sessionId)
            if (response.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception("Purge failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun mapResponseToDomain(dto: AnalyzeResponseDto): AnalysisResult {
        return when (dto.status) {
            "EMERGENCY_INTERCEPTION" -> {
                AnalysisResult.Emergency(
                    helplines = dto.helplines?.map {
                        EmergencyContact(
                            title = it.title,
                            number = it.number,
                            description = it.description
                        )
                    } ?: emptyList(),
                    advisory = dto.advisory ?: "Immediate emergency safety intervention required."
                )
            }

            "NEEDS_CLARIFICATION" -> {
                val qDto = dto.question ?: throw IllegalStateException("Question payload missing in NEEDS_CLARIFICATION response")
                AnalysisResult.NeedsClarification(
                    sessionId = dto.sessionId ?: "",
                    currentStep = dto.currentStep ?: 1,
                    maxSteps = dto.maxSteps ?: 5,
                    remainingCandidates = dto.remainingCandidatesCount ?: 0,
                    question = ClarificationQuestion(
                        factKey = qDto.factKey,
                        questionText = qDto.questionText,
                        observableProxyHint = qDto.observableProxyHint,
                        category = qDto.category,
                        informationGainBits = qDto.informationGainBits
                    ),
                    primaryRegime = dto.primaryLegalRegime ?: "BNS"
                )
            }

            "COMPLETED" -> {
                AnalysisResult.Completed(
                    sessionId = dto.sessionId ?: "",
                    primaryRegime = dto.primaryLegalRegime ?: "BNS",
                    primaryProvisions = dto.provisions?.map {
                        ProvisionMatch(
                            provisionId = it.provisionId,
                            sectionNumber = it.sectionNumber,
                            actName = it.actName,
                            primaryCitation = it.primaryCitation,
                            crossReferenceCitation = it.crossReferenceCitation,
                            title = it.title,
                            plainSummary = it.plainSummary,
                            punishment = it.punishment,
                            isCognizable = it.isCognizable,
                            isBailable = it.isBailable,
                            compoundableType = it.compoundableType,
                            triableBy = it.triableBy,
                            posteriorProbability = it.posteriorProbability,
                            matchedFacts = it.matchedFacts
                        )
                    } ?: emptyList(),
                    lesserOffences = dto.lesserIncludedOffences?.map {
                        LesserOffenceMatch(
                            provisionId = it.provisionId,
                            sectionNumber = it.sectionNumber,
                            title = it.title,
                            relationType = it.relationType,
                            punishment = it.punishment,
                            isCognizable = it.isCognizable,
                            isBailable = it.isBailable
                        )
                    } ?: emptyList(),
                    auditTrail = dto.auditTrail?.map {
                        AuditStep(
                            step = it.step,
                            action = it.action,
                            factKey = it.factKey,
                            answer = it.answer,
                            entropy = it.entropy,
                            maxProbability = it.maxProbability
                        )
                    } ?: emptyList()
                )
            }

            else -> throw IllegalArgumentException("Unknown response status: ${dto.status}")
        }
    }
}

