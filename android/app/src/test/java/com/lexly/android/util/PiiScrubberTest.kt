package com.lexly.android.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PiiScrubberTest {

    @Test
    fun `test scrub replaces Indian phone numbers`() {
        val input = "Call me at +91 9876543210 or 9123456789 regarding the land dispute."
        val scrubbed = PiiScrubber.scrub(input)
        assertEquals("Call me at [REDACTED_PHONE] or [REDACTED_PHONE] regarding the land dispute.", scrubbed)
    }

    @Test
    fun `test scrub replaces 12-digit Aadhaar numbers`() {
        val input = "My Aadhaar card number is 2345 6789 0123 for verification."
        val scrubbed = PiiScrubber.scrub(input)
        assertEquals("My Aadhaar card number is [REDACTED_AADHAAR] for verification.", scrubbed)
    }

    @Test
    fun `test scrub replaces Indian PAN card format`() {
        val input = "Submit your PAN ABCDE1234F to the revenue authority."
        val scrubbed = PiiScrubber.scrub(input)
        assertEquals("Submit your PAN [REDACTED_PAN] to the revenue authority.", scrubbed)
    }

    @Test
    fun `test scrub replaces email addresses`() {
        val input = "Send documents to lawyer.sharma@example.gov.in immediately."
        val scrubbed = PiiScrubber.scrub(input)
        assertEquals("Send documents to [REDACTED_EMAIL] immediately.", scrubbed)
    }

    @Test
    fun `test containsPii detects sensitive information`() {
        assertTrue(PiiScrubber.containsPii("Contact 9876543210"))
        assertTrue(PiiScrubber.containsPii("UIDAI: 234567890123"))
        assertTrue(PiiScrubber.containsPii("Tax ID: ABCDE1234F"))
        assertTrue(PiiScrubber.containsPii("Mail: user@test.com"))
        assertFalse(PiiScrubber.containsPii("The landlord locked the premises without statutory notice."))
    }

    @Test
    fun `test empty and blank input returns unchanged`() {
        assertEquals("", PiiScrubber.scrub(""))
        assertEquals("   ", PiiScrubber.scrub("   "))
        assertFalse(PiiScrubber.containsPii(""))
    }
}

