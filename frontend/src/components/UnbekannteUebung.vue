<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const {t} = useI18n()
</script>

<template>
    <main class="mx-auto flex max-w-xl flex-col gap-2 p-6">
        <h1 class="m-0 text-xl font-bold">{{ t('unbekannt.titel') }}</h1>
        <p class="m-0 text-muted">{{ t('unbekannt.text') }}</p>
        <RouterLink to="/" class="font-semibold text-primary">{{ t('unbekannt.zurueck') }}</RouterLink>
    </main>
</template>
