<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {dauer} from '../composables/useUhr'
import type {Anruf} from '../modell/uebung'

const props = defineProps<{anrufe: Anruf[], gewaehlt?: string}>()
const emit = defineEmits<{waehlen: [anrufId: string]}>()

const {t} = useI18n()
const liste = computed(() => [...props.anrufe].reverse())

/**
 * What became of a call, with how long it took.
 *
 * @param anruf the call
 * @returns the line shown in the log
 */
function verlauf(anruf: Anruf): string {
    if (anruf.zustand === 'aufgelegt') return t('protokoll.aufgelegt', {zeit: dauer((anruf.beendetUm ?? anruf.klingeltSeit) - anruf.klingeltSeit)})
    if (anruf.zustand === 'wartet') return t('protokoll.wartet')
    const angenommen = anruf.angenommenUm ?? anruf.klingeltSeit
    const annahme = t('protokoll.angenommen', {zeit: dauer(angenommen - anruf.klingeltSeit)})
    if (anruf.zustand === 'gespraech') return `${annahme} · ${t('protokoll.laeuft')}`
    return `${annahme} · ${t('protokoll.beendet', {zeit: dauer((anruf.beendetUm ?? angenommen) - angenommen)})}`
}
</script>

<template>
    <section :aria-label="t('protokoll.titel')" class="flex flex-col gap-2">
        <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('protokoll.titel') }}</h2>
        <p v-if="liste.length === 0" class="m-0 text-sm text-gedaempft">{{ t('protokoll.leer') }}</p>
        <ol class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
            <li v-for="anruf in liste" :key="anruf.id">
                <button type="button" :aria-pressed="anruf.id === gewaehlt" :class="['flex w-full flex-wrap gap-x-2 rounded border px-2 py-1 text-left', anruf.id === gewaehlt ? 'border-tinte bg-slate-100' : 'border-rand']" @click="emit('waehlen', anruf.id)">
                    <b>{{ anruf.szenario.titel }}</b>
                    <span class="font-mono text-xs">{{ anruf.szenario.ziel.code }}</span>
                    <span class="text-gedaempft">{{ verlauf(anruf) }}</span>
                </button>
            </li>
        </ol>
    </section>
</template>
