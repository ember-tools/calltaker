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
            :class="['flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold', stand.fehlend.length === 0 ? 'bg-success/15 text-success' : stand.phase.id === aktiv ? 'bg-primary text-inverted' : 'border border-accented bg-default text-muted']"
        >
            <UIcon v-if="stand.fehlend.length === 0" name="i-lucide-check" class="size-3.5" aria-hidden="true"/>
            {{ stelle + 1 }} {{ t(stand.phase.titel) }}
        </span>
    </nav>
</template>
