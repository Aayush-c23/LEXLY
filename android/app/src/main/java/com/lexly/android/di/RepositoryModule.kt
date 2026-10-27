package com.lexly.android.di

import com.lexly.android.data.repository.LexlyRepositoryImpl
import com.lexly.android.domain.repository.LexlyRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindLexlyRepository(
        impl: LexlyRepositoryImpl
    ): LexlyRepository
}

