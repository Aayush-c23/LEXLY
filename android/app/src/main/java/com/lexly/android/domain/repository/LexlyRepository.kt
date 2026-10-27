package com.lexly.android.domain.repository

import com.lexly.android.domain.model.AnalysisResult

interface LexlyRepository {
    suspend fun analyzeScenario(
        scenario: String,
        incidentDate: String?,
        locale: String
    ): Result<AnalysisResult>

    suspend fun submitAnswer(
        sessionId: String,
        step: Int,
        factKey: String,
        answer: String,
        locale: String
    ): Result<AnalysisResult>

    suspend fun undoStep(
        sessionId: String,
        targetStep: Int,
        locale: String
    ): Result<AnalysisResult>

    suspend fun purgeSession(
        sessionId: String
    ): Result<Boolean>
}

