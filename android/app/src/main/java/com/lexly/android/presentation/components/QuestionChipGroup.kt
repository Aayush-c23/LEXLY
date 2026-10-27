package com.lexly.android.presentation.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.lexly.android.R
import com.lexly.android.presentation.theme.NoRedContainerLight
import com.lexly.android.presentation.theme.NoRedLight
import com.lexly.android.presentation.theme.YesGreenContainerLight
import com.lexly.android.presentation.theme.YesGreenLight

@Composable
fun QuestionChipGroup(
    isSubmitting: Boolean,
    onAnswerSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // 1. YES Action Chip (Green Tint, Checkmark Icon, min 48dp)
        Button(
            onClick = { if (!isSubmitting) onAnswerSelected("YES") },
            enabled = !isSubmitting,
            modifier = Modifier
                .weight(1f)
                .height(52.dp)
                .semantics {
                    role = Role.Button
                    contentDescription = "Answer Yes: Confirms this factual ingredient"
                },
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = YesGreenContainerLight,
                contentColor = YesGreenLight
            ),
            elevation = ButtonDefaults.buttonElevation(defaultElevation = 1.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Check,
                contentDescription = null,
                tint = YesGreenLight,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = stringResource(R.string.chip_yes),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp
                ),
                color = YesGreenLight
            )
        }

        // 2. NO Action Chip (Red Tint, Cross Icon, min 48dp)
        Button(
            onClick = { if (!isSubmitting) onAnswerSelected("NO") },
            enabled = !isSubmitting,
            modifier = Modifier
                .weight(1f)
                .height(52.dp)
                .semantics {
                    role = Role.Button
                    contentDescription = "Answer No: Denies this factual ingredient"
                },
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = NoRedContainerLight,
                contentColor = NoRedLight
            ),
            elevation = ButtonDefaults.buttonElevation(defaultElevation = 1.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = null,
                tint = NoRedLight,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = stringResource(R.string.chip_no),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp
                ),
                color = NoRedLight
            )
        }

        // 3. NOT SURE Action Chip (Neutral Outline, Question Icon, min 48dp)
        OutlinedButton(
            onClick = { if (!isSubmitting) onAnswerSelected("NOT_SURE") },
            enabled = !isSubmitting,
            modifier = Modifier
                .weight(1.1f)
                .height(52.dp)
                .semantics {
                    role = Role.Button
                    contentDescription = "Answer Not Sure: Fact is unknown or uncertain"
                },
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.5.dp, MaterialTheme.colorScheme.outline),
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = MaterialTheme.colorScheme.onSurface
            )
        ) {
            Icon(
                imageVector = Icons.Default.HelpOutline,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = stringResource(R.string.chip_not_sure),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 11.sp
                ),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

