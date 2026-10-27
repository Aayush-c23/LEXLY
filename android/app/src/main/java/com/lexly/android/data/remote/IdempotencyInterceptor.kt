package com.lexly.android.data.remote

import okhttp3.Interceptor
import okhttp3.Response
import java.util.UUID

class IdempotencyInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        if (originalRequest.method.equals("POST", ignoreCase = true) &&
            originalRequest.header("Idempotency-Key") == null
        ) {
            val authenticatedRequest = originalRequest.newBuilder()
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .build()
            return chain.proceed(authenticatedRequest)
        }

        return chain.proceed(originalRequest)
    }
}

