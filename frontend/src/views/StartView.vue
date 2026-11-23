<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const {t} = useI18n()
</script>

<template>
    <main class="min-h-screen flex flex-col items-center justify-center gap-2 p-6">
        <h1 class="m-0 font-condensed text-4xl font-bold tracking-wide">{{ t('app.name') }}</h1>
        <p class="m-0 text-gedaempft">{{ t('app.untertitel') }}</p>
    </main>
</template>
