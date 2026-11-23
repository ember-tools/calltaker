<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import type {Phasenstand} from '../phasen/register'

defineProps<{staende: Phasenstand[], aktiv: string}>()

const {t} = useI18n()
</script>

<template>
    <nav :aria-label="t('phase.leiste')" class="flex flex-wrap gap-2">
        <span
            v-for="(stand, stelle) in staende"
            :key="stand.phase.id"
            :class="['flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold', stand.fehlend.length === 0 ? 'bg-green-100 text-ok' : stand.phase.id === aktiv ? 'bg-akzent text-white' : 'border border-slate-300 bg-white text-gedaempft']"
        >
            <svg v-if="stand.fehlend.length === 0" class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
            {{ stelle + 1 }} {{ t(stand.phase.titel) }}
        </span>
    </nav>
</template>
