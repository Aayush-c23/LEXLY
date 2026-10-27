package com.lexly.android.presentation.screens

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.lexly.android.presentation.AnalysisUiIntent
import com.lexly.android.presentation.AnalysisUiState
import com.lexly.android.presentation.AnalysisViewModel
import com.lexly.android.presentation.components.DpdpConsentDialog
import com.lexly.android.presentation.components.EmergencyBanner
import com.lexly.android.presentation.components.ScenarioInputCard
import com.lexly.android.presentation.theme.LegalNavy
import com.lexly.android.presentation.theme.NoRedLight

@Composable
fun LexlyMainScreen(
    viewModel: AnalysisViewModel = hiltViewModel(),
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            AnimatedContent(
                targetState = uiState,
                transitionSpec = { fadeIn() togetherWith fadeOut() },
                label = "MainScreenTransition"
            ) { state ->
                when (state) {
                    is AnalysisUiState.InputState -> {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .verticalScroll(rememberScrollState())
                                .padding(16.dp),
                            contentAlignment = Alignment.TopCenter
                        ) {
                            ScenarioInputCard(
                                text = state.text,
                                incidentDate = state.incidentDate,
                                isValid = state.isValid,
                                isLoading = state.isLoading,
                                locale = state.locale,
                                errorMessage = state.errorMessage,
                                onTextChange = { viewModel.processIntent(AnalysisUiIntent.UpdateScenarioText(it)) },
                                onDateChange = { viewModel.processIntent(AnalysisUiIntent.UpdateIncidentDate(it)) },
                                onLocaleChange = { viewModel.processIntent(AnalysisUiIntent.ChangeLocale(it)) },
                                onSubmit = { viewModel.processIntent(AnalysisUiIntent.SubmitScenario) }
                            )

                            if (state.showConsentDialog) {
                                DpdpConsentDialog(
                                    onDismissRequest = { viewModel.processIntent(AnalysisUiIntent.DismissConsentDialog) },
                                    onConfirmConsent = { viewModel.processIntent(AnalysisUiIntent.AcceptConsent) }
                                )
                            }
                        }
                    }

                    is AnalysisUiState.InquiryState -> {
                        InquiryScreen(
                            state = state,
                            onAnswerSelected = { answer ->
                                viewModel.processIntent(AnalysisUiIntent.AnswerQuestion(answer))
                            },
                            onUndoClick = {
                                viewModel.processIntent(AnalysisUiIntent.UndoStep)
                            }
                        )
                    }

                    is AnalysisUiState.CompletedState -> {
                        ResultScreen(
                            state = state,
                            onResetClick = {
                                viewModel.processIntent(AnalysisUiIntent.ResetSession)
                            }
                        )
                    }

                    is AnalysisUiState.EmergencyState -> {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(20.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            EmergencyBanner(
                                helplines = state.helplines,
                                advisory = state.advisory
                            )
                        }
                    }

                    is AnalysisUiState.ErrorState -> {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(20.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Card(
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(
                                    modifier = Modifier.padding(24.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Text(
                                        text = "Connection / Analysis Error",
                                        style = MaterialTheme.typography.titleLarge.copy(
                                            fontWeight = FontWeight.Bold,
                                            color = NoRedLight
                                        )
                                    )
                                    Spacer(modifier = Modifier.height(10.dp))
                                    Text(
                                        text = state.message,
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Spacer(modifier = Modifier.height(20.dp))
                                    Button(
                                        onClick = { viewModel.processIntent(AnalysisUiIntent.RetryLastAction) },
                                        shape = RoundedCornerShape(10.dp),
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = LegalNavy,
                                            contentColor = Color.White
                                        )
                                    ) {
                                        Text("Retry")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

