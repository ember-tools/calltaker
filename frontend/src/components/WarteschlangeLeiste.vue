<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {dauer, useUhr} from '../composables/useUhr'
import {useKlingelton} from '../composables/useKlingelton'
import {anzeigen} from '../modell/rufnummer'
import type {AnrufSicht, TraineeZustand} from '../modell/uebung'

const props = defineProps<{zustand: TraineeZustand}>()
const emit = defineEmits<{bereit: [], annehmen: [anrufId: string]}>()

const {t} = useI18n()
const jetzt = useUhr()
const wartend = computed(() => props.zustand.anrufe.filter(anruf => anruf.zustand === 'wartet'))
const gespraech = computed(() => props.zustand.anrufe.find(anruf => anruf.zustand === 'gespraech'))
const klingelt = computed(() => wartend.value.length > 0 && !gespraech.value && !props.zustand.engine.pausiert)
const klingelton = useKlingelton(klingelt)

function wartezeit(anruf: AnrufSicht): string {
    const bis = props.zustand.engine.pausiertSeit ?? jetzt.value
    return dauer(bis - anruf.klingeltSeit)
}

function nummer(anruf: AnrufSicht): string {
    return anruf.rufnummer ? anzeigen(anruf.rufnummer) : t('warteschlange.unterdrueckt')
}
</script>

<template>
    <div class="flex flex-wrap items-center gap-3">
        <button v-if="!zustand.engine.gestartet" type="button" class="h-9 rounded bg-green-600 px-4 font-semibold text-white" @click="emit('bereit')">{{ t('warteschlange.bereit') }}</button>
        <span v-if="!zustand.engine.gestartet" class="text-sm text-slate-300">{{ t('warteschlange.bereitText') }}</span>
        <span class="text-xs font-semibold tracking-wider text-slate-300">{{ t('warteschlange.titel') }}</span>
        <span v-if="wartend.length === 0" class="text-sm text-slate-400">{{ t('warteschlange.leer') }}</span>
        <div v-for="(anruf, stelle) in wartend" :key="anruf.id" :class="['flex items-center gap-2.5 rounded-md border px-3 py-1', stelle === 0 ? 'border-amber-400 bg-amber-950' : 'border-slate-600 bg-slate-800']">
            <span class="font-mono text-sm">{{ nummer(anruf) }}</span>
            <span class="font-mono text-sm text-amber-300">{{ wartezeit(anruf) }}</span>
            <button v-if="stelle === 0 && !gespraech" type="button" class="h-7 rounded bg-amber-500 px-2.5 text-sm font-semibold text-slate-900" @click="emit('annehmen', anruf.id)">{{ t('warteschlange.annehmen') }}</button>
        </div>
        <span v-if="zustand.engine.pausiert" class="rounded bg-slate-600 px-2 py-0.5 text-xs font-semibold">{{ t(zustand.engine.automatischPausiert ? 'warteschlange.automatisch' : 'warteschlange.pausiert') }}</span>
        <label class="ml-auto flex items-center gap-1.5 text-xs text-slate-300">
            <input v-model="klingelton" type="checkbox"/>
            {{ t('warteschlange.klingelton') }}
        </label>
        <div v-if="gespraech" class="flex items-center gap-2.5 rounded-md border border-green-400 bg-green-950 px-3 py-1">
            <span class="text-xs font-bold text-green-300">{{ t('warteschlange.imGespraech') }}</span>
            <span class="font-mono">{{ nummer(gespraech) }}</span>
            <span class="font-mono text-green-300">{{ dauer(jetzt - (gespraech.angenommenUm ?? jetzt)) }}</span>
        </div>
    </div>
</template>
