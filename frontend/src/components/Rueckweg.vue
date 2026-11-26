<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import type {Rolle} from '../modell/uebung'

defineProps<{code: string, rolle: Rolle}>()

const {t} = useI18n()
</script>

<template>
    <nav :aria-label="t('auswertung.navigation')" class="flex gap-3 text-sm">
        <RouterLink :to="{name: rolle, params: {code}}" class="underline">{{ t('auswertung.zurueck') }}</RouterLink>
        <RouterLink :to="{name: `${rolle}-uebersicht`, params: {code}}" class="underline">{{ t('auswertung.uebersicht') }}</RouterLink>
    </nav>
</template>
