package com.lexly.android.presentation.screens

import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Balance
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.lexly.android.R
import com.lexly.android.presentation.AnalysisUiState
import com.lexly.android.presentation.components.AuditTrailCard
import com.lexly.android.presentation.components.ProvisionCard
import com.lexly.android.presentation.theme.LegalGold
import com.lexly.android.presentation.theme.LegalNavy

@Composable
fun ResultScreen(
    state: AnalysisUiState.CompletedState,
    onResetClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Legal Regime Banner
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (state.primaryRegime == "BNS") Color(0xFFE8EEF5) else Color(0xFFFFF3E0)
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Balance,
                    contentDescription = null,
                    tint = if (state.primaryRegime == "BNS") LegalNavy else Color(0xFFBF360C),
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = if (state.primaryRegime == "BNS") {
                            "Governing Scheme: Bharatiya Nyaya Sanhita, 2023"
                        } else {
                            "Governing Scheme: Indian Penal Code, 1860"
                        },
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = if (state.primaryRegime == "BNS") LegalNavy else Color(0xFFBF360C)
                    )
                    Text(
                        text = "Cross-referenced with corresponding legacy & new penal provisions",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Section Title
        Text(
            text = stringResource(R.string.results_title),
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface
        )

        // Primary Applicable Provisions List
        state.primaryProvisions.forEach { provision ->
            ProvisionCard(provision = provision)
        }

        // Lesser Included & Subsidiary Offences
        if (state.lesserOffences.isNotEmpty()) {
            Text(
                text = stringResource(R.string.lesser_offences_title),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(top = 8.dp)
            )

            state.lesserOffences.forEach { lesser ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "Section ${lesser.sectionNumber}: ${lesser.title}",
                                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                                color = LegalNavy
                            )
                            Text(
                                text = "Subsidiary: ${lesser.relationType}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }

        // Analytical Audit Trail (Entropy Reduction)
        if (state.auditTrail.isNotEmpty()) {
            AuditTrailCard(auditSteps = state.auditTrail)
        }

        // Action Buttons: Share Summary & Start Over
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(
                onClick = {
                    val summaryText = buildString {
                        appendLine("=== LEXLY Legal Analysis Summary ===")
                        appendLine("Governing Regime: ${state.primaryRegime}")
                        appendLine()
                        appendLine("Applicable Provisions:")
                        state.primaryProvisions.forEach { p ->
                            appendLine("• Section ${p.sectionNumber} (${p.actName}): ${p.title}")
                            appendLine("  Citation: ${p.primaryCitation} | Cross-ref: ${p.crossReferenceCitation}")
                            appendLine("  Punishment: ${p.punishment}")
                            appendLine("  Procedural: ${if (p.isCognizable) "Cognizable" else "Non-Cognizable"}, ${if (p.isBailable) "Bailable" else "Non-Bailable"}")
                            appendLine()
                        }
                        appendLine("Disclaimers: Informational only under Indian law. Not formal legal counsel.")
                    }

                    val sendIntent = Intent().apply {
                        action = Intent.ACTION_SEND
                        putExtra(Intent.EXTRA_TEXT, summaryText)
                        type = "text/plain"
                    }
                    context.startActivity(Intent.createChooser(sendIntent, "Share Legal Summary"))
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = LegalNavy,
                    contentColor = Color.White
                )
            ) {
                Icon(
                    imageVector = Icons.Default.Share,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.share_summary),
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold)
                )
            }

            OutlinedButton(
                onClick = onResetClick,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.action_reset),
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold)
                )
            }
        }
    }
}

