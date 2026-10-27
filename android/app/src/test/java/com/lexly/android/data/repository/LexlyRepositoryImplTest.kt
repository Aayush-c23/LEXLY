package com.lexly.android.data.repository

import com.lexly.android.data.remote.LexlyApiService
import com.lexly.android.data.remote.dto.AnalyzeResponseDto
import com.lexly.android.data.remote.dto.ClarificationQuestionDto
import com.lexly.android.data.remote.dto.EmergencyContactDto
import com.lexly.android.data.remote.dto.ProvisionResultDto
import com.lexly.android.data.remote.dto.PurgeResponseDto
import com.lexly.android.domain.model.AnalysisResult
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

class LexlyRepositoryImplTest {

    private val apiService: LexlyApiService = mockk()
    private lateinit var repository: LexlyRepositoryImpl

    @Before
    fun setUp() {
        repository = LexlyRepositoryImpl(apiService)
    }

    @Test
    fun `analyzeScenario returns Emergency result on emergency status`() = runTest {
        val dto = AnalyzeResponseDto(
            status = "EMERGENCY_INTERCEPTION",
            helplines = listOf(
                EmergencyContactDto("Police", "112", "Emergency contact")
            ),
            advisory = "Call emergency services immediately."
        )

        coEvery { apiService.analyze(any(), any()) } returns Response.success(dto)

        val result = repository.analyzeScenario("Help me", null, "en")
        assertTrue(result.isSuccess)
        val data = result.getOrNull()
        assertTrue(data is AnalysisResult.Emergency)
        val emergency = data as AnalysisResult.Emergency
        assertEquals("112", emergency.helplines.first().number)
    }

    @Test
    fun `analyzeScenario returns NeedsClarification on inquiry status`() = runTest {
        val dto = AnalyzeResponseDto(
            status = "NEEDS_CLARIFICATION",
            sessionId = "sess-456",
            currentStep = 1,
            maxSteps = 5,
            primaryLegalRegime = "BNS",
            remainingCandidatesCount = 12,
            question = ClarificationQuestionDto(
                factKey = "physical_contact",
                questionText = "Was physical contact made?",
                observableProxyHint = "Punching, slapping",
                category = "body",
                informationGainBits = 0.28
            )
        )

        coEvery { apiService.analyze(any(), any()) } returns Response.success(dto)

        val result = repository.analyzeScenario("A street altercation took place", "2024-08-01", "en")
        assertTrue(result.isSuccess)
        val data = result.getOrNull()
        assertTrue(data is AnalysisResult.NeedsClarification)
        val inquiry = data as AnalysisResult.NeedsClarification
        assertEquals("sess-456", inquiry.sessionId)
        assertEquals("physical_contact", inquiry.question.factKey)
        assertEquals("BNS", inquiry.primaryRegime)
    }

    @Test
    fun `analyzeScenario returns Completed on completion status`() = runTest {
        val dto = AnalyzeResponseDto(
            status = "COMPLETED",
            sessionId = "sess-789",
            primaryLegalRegime = "BNS",
            provisions = listOf(
                ProvisionResultDto(
                    provisionId = 1,
                    sectionNumber = "115(2)",
                    actName = "Bharatiya Nyaya Sanhita, 2023",
                    primaryCitation = "Section 115(2) BNS",
                    crossReferenceCitation = "Section 323 IPC",
                    title = "Voluntarily causing hurt",
                    plainSummary = "Inflicting physical bodily pain or swelling.",
                    punishment = "Imprisonment up to 1 year, or fine.",
                    isCognizable = false,
                    isBailable = true,
                    compoundableType = "COMPOUNDABLE",
                    triableBy = "Any Magistrate",
                    posteriorProbability = 0.94,
                    matchedFacts = mapOf("physical_contact" to "TRUE")
                )
            )
        )

        coEvery { apiService.analyze(any(), any()) } returns Response.success(dto)

        val result = repository.analyzeScenario("A vendor slapped a customer", "2024-08-01", "en")
        assertTrue(result.isSuccess)
        val data = result.getOrNull()
        assertTrue(data is AnalysisResult.Completed)
        val completed = data as AnalysisResult.Completed
        assertEquals("115(2)", completed.primaryProvisions.first().sectionNumber)
        assertEquals("Section 323 IPC", completed.primaryProvisions.first().crossReferenceCitation)
    }

    @Test
    fun `analyzeScenario returns failure on HTTP error code`() = runTest {
        coEvery { apiService.analyze(any(), any()) } returns Response.error(
            500,
            "Internal server error".toResponseBody()
        )

        val result = repository.analyzeScenario("A test scenario", null, "en")
        assertTrue(result.isFailure)
    }

    @Test
    fun `purgeSession returns success on 200 DELETE response`() = runTest {
        coEvery { apiService.deleteSession("sess-123") } returns Response.success(
            PurgeResponseDto("sess-123", "PURGED")
        )

        val result = repository.purgeSession("sess-123")
        assertTrue(result.isSuccess)
        assertEquals(true, result.getOrNull())
    }
}

