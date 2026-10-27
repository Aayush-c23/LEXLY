package com.lexly.android.util

import java.util.regex.Pattern

/**
 * Client-Side PII Scrubber for Indian Digital Personal Data Protection (DPDP) Act 2023 compliance.
 *
 * Ensures that sensitive personal data (Aadhaar, PAN, Indian phone numbers, emails)
 * is redacted before being transmitted across network boundaries or stored locally.
 */
object PiiScrubber {

    // Indian Phone Numbers (+91 or 0 followed by 10 digits starting with 6-9, or standalone 10 digits)
    private val PHONE_PATTERN = Pattern.compile(
        """(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\b"""
    )

    // Indian Aadhaar Number (12 digits, often formatted as 4-4-4)
    private val AADHAAR_PATTERN = Pattern.compile(
        """\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"""
    )

    // Indian Permanent Account Number (PAN) (5 letters, 4 digits, 1 letter)
    private val PAN_PATTERN = Pattern.compile(
        """\b[A-Z]{5}[0-9]{4}[A-Z]\b""",
        Pattern.CASE_INSENSITIVE
    )

    // Email Address
    private val EMAIL_PATTERN = Pattern.compile(
        """\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"""
    )

    /**
     * Replaces detected PII tokens in the input text with standardized redaction placeholders.
     */
    fun scrub(input: String): String {
        if (input.isBlank()) return input

        var scrubbed = input
        scrubbed = AADHAAR_PATTERN.matcher(scrubbed).replaceAll("[REDACTED_AADHAAR]")
        scrubbed = PAN_PATTERN.matcher(scrubbed).replaceAll("[REDACTED_PAN]")
        scrubbed = PHONE_PATTERN.matcher(scrubbed).replaceAll("[REDACTED_PHONE]")
        scrubbed = EMAIL_PATTERN.matcher(scrubbed).replaceAll("[REDACTED_EMAIL]")

        return scrubbed
    }

    /**
     * Returns true if any PII pattern is detected in the input string.
     */
    fun containsPii(input: String): Boolean {
        if (input.isBlank()) return false
        return AADHAAR_PATTERN.matcher(input).find() ||
                PAN_PATTERN.matcher(input).find() ||
                PHONE_PATTERN.matcher(input).find() ||
                EMAIL_PATTERN.matcher(input).find()
    }
}

