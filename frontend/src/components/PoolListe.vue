<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import type {Befund, Szenario} from '../modell/szenario'

defineProps<{pool: Szenario[], befunde: Record<string, Befund[]>, gewaehlt?: string, gesperrt?: boolean}>()
const emit = defineEmits<{bearbeiten: [id: string], entfernen: [id: string], verschieben: [id: string, ziel: number]}>()

const {t} = useI18n()

/**
 * How a scenario's findings read in the list.
 *
 * @param liste the findings
 * @returns the marker text, or an empty text without findings
 */
function markierung(liste: Befund[] | undefined): string {
    if (!liste?.length) return ''
    const fehler = liste.filter(b => b.art === 'fehler').length
    return fehler ? t('pool.fehler', {anzahl: fehler}) : t('pool.warnungen', {anzahl: liste.length})
}
</script>

<template>
    <ol class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
        <li v-for="(szenario, stelle) in pool" :key="szenario.id" :class="['flex items-center gap-2 rounded border px-2 py-1', szenario.id === gewaehlt ? 'border-inverted' : 'border-default']">
            <span class="w-6 text-right text-muted">{{ stelle + 1 }}</span>
            <span class="flex-1">
                <b>{{ szenario.titel }}</b>
                <span class="ml-2 font-mono text-xs">{{ szenario.ziel.code }}</span>
                <span v-if="szenario.herkunft === 'generiert'" class="ml-2 text-xs text-muted">{{ t('pool.generiert') }}</span>
                <span v-if="markierung(befunde[szenario.id])" :class="['ml-2 text-xs font-semibold', befunde[szenario.id]!.some(b => b.art === 'fehler') ? 'text-error' : 'text-warning']">{{ markierung(befunde[szenario.id]) }}</span>
            </span>
            <UButton color="neutral" variant="ghost" size="sm" :disabled="stelle === 0" :aria-label="t('pool.hoch', {titel: szenario.titel})" @click="emit('verschieben', szenario.id, stelle - 1)"><UIcon name="i-lucide-arrow-up" aria-hidden="true"/></UButton>
            <UButton color="neutral" variant="ghost" size="sm" :disabled="stelle === pool.length - 1" :aria-label="t('pool.runter', {titel: szenario.titel})" @click="emit('verschieben', szenario.id, stelle + 1)"><UIcon name="i-lucide-arrow-down" aria-hidden="true"/></UButton>
            <UButton color="neutral" variant="link" size="xs" :disabled="gesperrt" @click="emit('bearbeiten', szenario.id)">{{ t('pool.bearbeiten') }}</UButton>
            <UButton color="error" variant="link" size="xs" @click="emit('entfernen', szenario.id)">{{ t('pool.entfernen') }}</UButton>
        </li>
    </ol>
</template>
