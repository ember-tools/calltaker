<script setup lang="ts">
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
    <section :aria-label="t('steuerung.titel')" class="flex flex-col gap-2 rounded-lg border border-default bg-default p-3 text-sm">
        <div class="flex flex-wrap items-center gap-3">
            <h2 class="section-title m-0">{{ t('steuerung.titel') }}</h2>
            <span v-if="!engine.gestartet" class="text-muted">{{ t('steuerung.wartetAufTrainee') }}</span>
            <span v-else-if="engine.automatischPausiert" class="rounded bg-accented px-2 py-0.5 text-xs font-semibold">{{ t('warteschlange.automatisch') }}</span>
            <span v-else-if="naechstes !== undefined" class="text-muted">{{ t('steuerung.naechstes', {zeit: dauer(naechstes)}) }}</span>
            <UButton color="neutral" variant="outline" size="sm" @click="senden('engine.pausieren', {an: !engine.manuellPausiert})"><UIcon :name="engine.manuellPausiert ? 'i-lucide-play' : 'i-lucide-pause'" class="mr-1" aria-hidden="true"/>{{ engine.manuellPausiert ? t('steuerung.weiter') : t('steuerung.pause') }}</UButton>
            <label class="flex items-center gap-1.5">
                <span class="sr-only">{{ t('steuerung.sofortWahl') }}</span>
                <select v-model="sofortId" class="native-field max-w-56">
                    <option value="">{{ t('steuerung.sofortWahl') }}</option>
                    <option v-for="szenario in zustand.pool" :key="szenario.id" :value="szenario.id">{{ szenario.titel }}</option>
                </select>
            </label>
            <UButton color="neutral" variant="outline" size="sm" :disabled="!sofortId" @click="sofort"><UIcon name="i-lucide-zap" class="mr-1" aria-hidden="true"/>{{ t('steuerung.sofort') }}</UButton>
        </div>
        <ul class="m-0 flex list-none flex-wrap gap-2 p-0">
            <li v-if="gespraech" class="flex items-center gap-2 rounded border border-success bg-success/10 px-2 py-1">
                <b>{{ t('steuerung.imGespraech') }}</b> {{ gespraech.szenario.titel }} <span class="font-mono">{{ gespraechsdauer(gespraech.angenommenUm, jetzt) }}</span>
            </li>
            <li v-for="anruf in wartend" :key="anruf.id" class="flex items-center gap-2 rounded border border-warning/60 bg-warning/10 px-2 py-1">
                {{ anruf.szenario.titel }} <span class="font-mono">{{ wartezeit(anruf.klingeltSeit, jetzt, engine.pausiertSeit) }}</span>
                <UButton color="neutral" variant="link" size="xs" @click="senden('anruf.auflegen', {anrufId: anruf.id})"><UIcon name="i-lucide-phone-off" class="mr-1" aria-hidden="true"/>{{ t('steuerung.auflegen') }}</UButton>
            </li>
            <li v-if="!gespraech && wartend.length === 0" class="text-muted">{{ t('warteschlange.leer') }}</li>
        </ul>
        <p v-if="fehler" class="m-0 text-error" role="alert">{{ fehler }}</p>
    </section>
</template>
