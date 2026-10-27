package com.lexly.android.presentation

import androidx.lifecycle.SavedStateHandle
import com.lexly.android.domain.model.AnalysisResult
import com.lexly.android.domain.model.ClarificationQuestion
import com.lexly.android.domain.model.EmergencyContact
import com.lexly.android.domain.model.ProvisionMatch
import com.lexly.android.domain.repository.LexlyRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AnalysisViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private val repository: LexlyRepository = mockk(relaxed = true)
    private lateinit var savedStateHandle: SavedStateHandle
    private lateinit var viewModel: AnalysisViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        savedStateHandle = SavedStateHandle(mapOf("saved_has_accepted_consent" to true))
        viewModel = AnalysisViewModel(repository, savedStateHandle)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `submitting without DPDP consent triggers consent dialog`() {
        val freshHandle = SavedStateHandle()
        val freshVm = AnalysisViewModel(repository, freshHandle)
        freshVm.processIntent(AnalysisUiIntent.UpdateScenarioText("Valid scenario text exceeding twenty characters"))
        freshVm.processIntent(AnalysisUiIntent.SubmitScenario)

        val state = freshVm.uiState.value as AnalysisUiState.InputState
        assertTrue(state.showConsentDialog)
        assertFalse(state.hasAcceptedConsent)

        freshVm.processIntent(AnalysisUiIntent.AcceptConsent)
        assertEquals(true, freshHandle.get<Boolean>("saved_has_accepted_consent"))
    }

    @Test
    fun `initial state is InputState and character count below 20 is invalid`() {
        val state = viewModel.uiState.value as AnalysisUiState.InputState
        assertFalse(state.isValid)
        assertEquals("", state.text)

        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText("Too short"))
        val updated = viewModel.uiState.value as AnalysisUiState.InputState
        assertFalse(updated.isValid)
    }

    @Test
    fun `character count between 20 and 2000 is marked valid`() {
        val validScenario = "A pedestrian was physically stopped from walking down the road towards his shop."
        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText(validScenario))

        val state = viewModel.uiState.value as AnalysisUiState.InputState
        assertTrue(state.isValid)
        assertEquals(validScenario, state.text)
    }

    @Test
    fun `submitting scenario transitioning to NeedsClarification updates state to InquiryState`() = runTest {
        val validScenario = "A pedestrian was physically stopped from walking down the road towards his shop."
        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText(validScenario))

        val mockQuestion = ClarificationQuestion(
            factKey = "wrongful_confinement",
            questionText = "Was the person locked inside a room?",
            observableProxyHint = "Barricaded room, padlocked doors.",
            category = "body",
            informationGainBits = 0.35
        )

        coEvery {
            repository.analyzeScenario(any(), any(), any())
        } returns Result.success(
            AnalysisResult.NeedsClarification(
                sessionId = "test-session-123",
                currentStep = 1,
                maxSteps = 5,
                remainingCandidates = 14,
                question = mockQuestion,
                primaryRegime = "BNS"
            )
        )

        viewModel.processIntent(AnalysisUiIntent.SubmitScenario)
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is AnalysisUiState.InquiryState)
        val inquiry = state as AnalysisUiState.InquiryState
        assertEquals("test-session-123", inquiry.sessionId)
        assertEquals(1, inquiry.currentStep)
        assertEquals("wrongful_confinement", inquiry.question.factKey)

        // Verify SavedStateHandle preserved session ID
        assertEquals("test-session-123", savedStateHandle.get<String>("saved_session_id"))
    }

    @Test
    fun `emergency response transitions state to EmergencyState`() = runTest {
        val emergencyScenario = "Someone is threatening my family with a loaded gun right now!"
        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText(emergencyScenario))

        coEvery {
            repository.analyzeScenario(any(), any(), any())
        } returns Result.success(
            AnalysisResult.Emergency(
                helplines = listOf(
                    EmergencyContact("Police", "112", "Emergency response")
                ),
                advisory = "Immediate danger detected."
            )
        )

        viewModel.processIntent(AnalysisUiIntent.SubmitScenario)
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is AnalysisUiState.EmergencyState)
        val emergency = state as AnalysisUiState.EmergencyState
        assertEquals("112", emergency.helplines.first().number)
    }

    @Test
    fun `answering question updates step and preserves state`() = runTest {
        // Setup initial inquiry state
        savedStateHandle["saved_session_id"] = "test-session-123"
        savedStateHandle["saved_current_step"] = 1

        val mockQ1 = ClarificationQuestion("fact_1", "Question 1", null, "body", 0.4)
        val mockQ2 = ClarificationQuestion("fact_2", "Question 2", null, "body", 0.2)

        coEvery {
            repository.analyzeScenario(any(), any(), any())
        } returns Result.success(
            AnalysisResult.NeedsClarification(
                sessionId = "test-session-123",
                currentStep = 1,
                maxSteps = 5,
                remainingCandidates = 10,
                question = mockQ1,
                primaryRegime = "BNS"
            )
        )

        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText("A valid incident description exceeding twenty characters."))
        viewModel.processIntent(AnalysisUiIntent.SubmitScenario)
        advanceUntilIdle()

        // Answer YES
        coEvery {
            repository.submitAnswer("test-session-123", 1, "fact_1", "YES", any())
        } returns Result.success(
            AnalysisResult.NeedsClarification(
                sessionId = "test-session-123",
                currentStep = 2,
                maxSteps = 5,
                remainingCandidates = 4,
                question = mockQ2,
                primaryRegime = "BNS"
            )
        )

        viewModel.processIntent(AnalysisUiIntent.AnswerQuestion("YES"))
        advanceUntilIdle()

        val state = viewModel.uiState.value as AnalysisUiState.InquiryState
        assertEquals(2, state.currentStep)
        assertEquals("fact_2", state.question.factKey)
        assertEquals(2, savedStateHandle.get<Int>("saved_current_step"))
    }

    @Test
    fun `undo step rolls back to previous inquiry step`() = runTest {
        val mockQ1 = ClarificationQuestion("fact_1", "Question 1", null, "body", 0.4)
        val mockQ2 = ClarificationQuestion("fact_2", "Question 2", null, "body", 0.2)

        coEvery {
            repository.analyzeScenario(any(), any(), any())
        } returns Result.success(
            AnalysisResult.NeedsClarification(
                sessionId = "test-session-123",
                currentStep = 2,
                maxSteps = 5,
                remainingCandidates = 4,
                question = mockQ2,
                primaryRegime = "BNS"
            )
        )

        viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText("A valid incident description exceeding twenty characters."))
        viewModel.processIntent(AnalysisUiIntent.SubmitScenario)
        advanceUntilIdle()

        // Mock undo to step 1
        coEvery {
            repository.undoStep("test-session-123", 1, any())
        } returns Result.success(
            AnalysisResult.NeedsClarification(
                sessionId = "test-session-123",
                currentStep = 1,
                maxSteps = 5,
                remainingCandidates = 10,
                question = mockQ1,
                primaryRegime = "BNS"
            )
        )

        viewModel.processIntent(AnalysisUiIntent.UndoStep)
        advanceUntilIdle()

        val state = viewModel.uiState.value as AnalysisUiState.InquiryState
        assertEquals(1, state.currentStep)
        assertEquals("fact_1", state.question.factKey)
    }

    @Test
    fun `reset session purges active session and restores clean input state`() = runTest {
        savedStateHandle["saved_session_id"] = "test-session-123"

        viewModel.processIntent(AnalysisUiIntent.ResetSession)
        advanceUntilIdle()

        coVerify { repository.purgeSession("test-session-123") }
        val state = viewModel.uiState.value
        assertTrue(state is AnalysisUiState.InputState)
    }
}

