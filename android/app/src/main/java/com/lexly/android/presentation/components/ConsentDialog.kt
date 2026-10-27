package com.lexly.android.presentation.components

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.lexly.android.R

/**
 * Explicit Indian DPDP Act 2023 Consent Dialog.
 *
 * Mandated under Section 6 of DPDP Act 2023:
 * Requires free, informed, specific, and unambiguous consent prior to processing
 * any factual personal or legal incident data.
 */
@Composable
fun DpdpConsentDialog(
    onDismissRequest: () -> Unit,
    onConfirmConsent: () -> Unit,
    modifier: Modifier = Modifier
) {
    AlertDialog(
        onDismissRequest = onDismissRequest,
        title = {
            Text(
                text = stringResource(id = R.string.dpdp_consent_title),
                style = MaterialTheme.typography.titleLarge
            )
        },
        text = {
            Text(
                text = stringResource(id = R.string.dpdp_consent_message),
                style = MaterialTheme.typography.bodyMedium
            )
        },
        confirmButton = {
            Button(
                onClick = onConfirmConsent
            ) {
                Text(text = stringResource(id = R.string.dpdp_agree))
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismissRequest
            ) {
                Text(text = stringResource(id = R.string.dpdp_decline))
            }
        },
        modifier = modifier
    )
}

