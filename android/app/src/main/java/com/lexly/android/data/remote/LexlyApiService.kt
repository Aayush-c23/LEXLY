package com.lexly.android.data.remote

import com.lexly.android.data.remote.dto.AnalyzeRequestDto
import com.lexly.android.data.remote.dto.AnalyzeResponseDto
import com.lexly.android.data.remote.dto.AnswerRequestDto
import com.lexly.android.data.remote.dto.PurgeResponseDto
import com.lexly.android.data.remote.dto.UndoRequestDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

interface LexlyApiService {
    @POST("analyze")
    suspend fun analyze(
        @Body request: AnalyzeRequestDto,
        @Header("Idempotency-Key") idempotencyKey: String? = null
    ): Response<AnalyzeResponseDto>

    @POST("session/{id}/answer")
    suspend fun answer(
        @Path("id") sessionId: String,
        @Body request: AnswerRequestDto,
        @Header("Idempotency-Key") idempotencyKey: String? = null
    ): Response<AnalyzeResponseDto>

    @POST("session/{id}/undo")
    suspend fun undo(
        @Path("id") sessionId: String,
        @Body request: UndoRequestDto
    ): Response<AnalyzeResponseDto>

    @DELETE("session/{id}")
    suspend fun deleteSession(
        @Path("id") sessionId: String
    ): Response<PurgeResponseDto>
}

