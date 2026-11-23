<script setup lang="ts">
import {faBolt, faPause, faPhoneSlash, faPlay} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {dauer, gespraechsdauer, useUhr, wartezeit} from '../composables/useUhr'
import type {AusbilderZustand} from '../modell/uebung'

const props = defineProps<{
    zustand: AusbilderZustand
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()

const {t} = useI18n()
const jetzt = useUhr()
const sofortId = ref('')
const fehler = ref('')
const engine = computed(() => props.zustand.engine)
const wartend = computed(() => props.zustand.anrufe.filter(anruf => anruf.zustand === 'wartet'))
const gespraech = computed(() => props.zustand.anrufe.find(anruf => anruf.zustand === 'gespraech'))
const naechstes = computed(() => (engine.value.naechstesKlingeln && !engine.value.pausiert ? Math.max(0, engine.value.naechstesKlingeln - jetzt.value) : undefined))

async function senden(art: string, daten: Record<string, unknown> = {}): Promise<boolean> {
    try {
        await props.absicht(art, daten)
        fehler.value = ''
        return true
    } catch (e) {
        fehler.value = (e as Error).message
        return false
    }
}

async function sofort(): Promise<void> {
    if (sofortId.value && await senden('engine.sofort', {szenarioId: sofortId.value})) sofortId.value = ''
}
</script>

<template>
    <section :aria-label="t('steuerung.titel')" class="flex flex-col gap-2 rounded-lg border border-rand bg-flaeche p-3 text-sm">
        <div class="flex flex-wrap items-center gap-3">
            <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('steuerung.titel') }}</h2>
            <span v-if="!engine.gestartet" class="text-gedaempft">{{ t('steuerung.wartetAufTrainee') }}</span>
            <span v-else-if="engine.automatischPausiert" class="rounded bg-slate-200 px-2 py-0.5 text-xs font-semibold">{{ t('warteschlange.automatisch') }}</span>
            <span v-else-if="naechstes !== undefined" class="text-gedaempft">{{ t('steuerung.naechstes', {zeit: dauer(naechstes)}) }}</span>
            <button type="button" class="rounded border border-slate-400 px-3 py-1 font-semibold" @click="senden('engine.pausieren', {an: !engine.manuellPausiert})"><FontAwesomeIcon :icon="engine.manuellPausiert ? faPlay : faPause" class="mr-1" aria-hidden="true"/>{{ engine.manuellPausiert ? t('steuerung.weiter') : t('steuerung.pause') }}</button>
            <label class="flex items-center gap-1.5">
                <span class="sr-only">{{ t('steuerung.sofortWahl') }}</span>
                <select v-model="sofortId" class="max-w-56 rounded border border-slate-400 px-1.5 py-1">
                    <option value="">{{ t('steuerung.sofortWahl') }}</option>
                    <option v-for="szenario in zustand.pool" :key="szenario.id" :value="szenario.id">{{ szenario.titel }}</option>
                </select>
            </label>
            <button type="button" :disabled="!sofortId" class="rounded border border-slate-400 px-3 py-1 font-semibold disabled:opacity-40" @click="sofort"><FontAwesomeIcon :icon="faBolt" class="mr-1" aria-hidden="true"/>{{ t('steuerung.sofort') }}</button>
        </div>
        <ul class="m-0 flex list-none flex-wrap gap-2 p-0">
            <li v-if="gespraech" class="flex items-center gap-2 rounded border border-green-600 bg-green-50 px-2 py-1">
                <b>{{ t('steuerung.imGespraech') }}</b> {{ gespraech.szenario.titel }} <span class="font-mono">{{ gespraechsdauer(gespraech.angenommenUm, jetzt) }}</span>
            </li>
            <li v-for="anruf in wartend" :key="anruf.id" class="flex items-center gap-2 rounded border border-amber-400 bg-amber-50 px-2 py-1">
                {{ anruf.szenario.titel }} <span class="font-mono">{{ wartezeit(anruf.klingeltSeit, jetzt, engine.pausiertSeit) }}</span>
                <button type="button" class="text-xs underline" @click="senden('anruf.auflegen', {anrufId: anruf.id})"><FontAwesomeIcon :icon="faPhoneSlash" class="mr-1" aria-hidden="true"/>{{ t('steuerung.auflegen') }}</button>
            </li>
            <li v-if="!gespraech && wartend.length === 0" class="text-gedaempft">{{ t('warteschlange.leer') }}</li>
        </ul>
        <p v-if="fehler" class="m-0 text-fehler" role="alert">{{ fehler }}</p>
    </section>
</template>
