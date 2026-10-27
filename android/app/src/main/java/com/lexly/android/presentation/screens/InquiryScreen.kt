package com.lexly.android.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.lexly.android.presentation.AnalysisUiState
import com.lexly.android.presentation.components.QuestionChipGroup
import com.lexly.android.presentation.components.StepProgressIndicator
import com.lexly.android.presentation.theme.LegalNavy

@Composable
fun InquiryScreen(
    state: AnalysisUiState.InquiryState,
    onAnswerSelected: (String) -> Unit,
    onUndoClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        // Step progress & candidate counter
        StepProgressIndicator(
            currentStep = state.currentStep,
            maxSteps = state.maxSteps,
            remainingCandidates = state.remainingCandidates,
            canUndo = state.currentStep > 1,
            onUndoClick = onUndoClick
        )

        // Question Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .semantics {
                    contentDescription = "Question ${state.currentStep}: ${state.question.questionText}. Hint: ${state.question.observableProxyHint ?: ""}"
                },
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Category pill
                Text(
                    text = state.question.category.uppercase(),
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = LegalNavy
                    )
                )

                // Question text in prominent typography
                Text(
                    text = state.question.questionText,
                    style = MaterialTheme.typography.headlineSmall.copy(
                        lineHeight = 28.sp,
                        fontWeight = FontWeight.SemiBold
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )

                // Observable Proxy Hint in muted italics
                if (!state.question.observableProxyHint.isNullOrBlank()) {
                    Text(
                        text = "Observable Indicators: ${state.question.observableProxyHint}",
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontStyle = FontStyle.Italic,
                            lineHeight = 20.sp
                        ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Tri-state action chips (YES / NO / NOT SURE)
                QuestionChipGroup(
                    isSubmitting = state.isSubmitting,
                    onAnswerSelected = onAnswerSelected
                )
            }
        }
    }
}

