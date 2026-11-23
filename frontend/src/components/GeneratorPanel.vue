<script setup lang="ts">
import {ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Gebiet} from '../api/gebiete'
import type {Erzeugung} from '../modell/uebung'
import {BESCHRIFTUNG, FELD} from './formular'
import GebietWahl from './GebietWahl.vue'

const props = defineProps<{
    erzeugung: Erzeugung
    autoGenerieren: boolean
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()

const {t} = useI18n()
const GEWICHTE = [
    {feld: 'gewichtRd', schluessel: 'generator.rd'},
    {feld: 'gewichtBrand', schluessel: 'generator.brand'},
    {feld: 'gewichtTh', schluessel: 'generator.th'},
] as const
const anzahl = ref(5)
const einstellung = ref<Erzeugung>({...props.erzeugung})
const meldung = ref('')
const fehler = ref(false)

watch(() => JSON.stringify(props.erzeugung), () => {
    einstellung.value = {...props.erzeugung}
})

async function senden(art: string, daten: Record<string, unknown>): Promise<Record<string, unknown> | undefined> {
    try {
        const ergebnis = await props.absicht(art, daten)
        fehler.value = false
        return ergebnis
    } catch (e) {
        meldung.value = (e as Error).message
        fehler.value = true
        return undefined
    }
}

async function einstellen(): Promise<void> {
    if (await senden('erzeugung.einstellen', {erzeugung: einstellung.value})) meldung.value = ''
}

async function gebietSetzen(gebiet: Gebiet): Promise<void> {
    einstellung.value = {...einstellung.value, ...gebiet}
    await einstellen()
}

async function generieren(): Promise<void> {
    const ergebnis = await senden('pool.generieren', {anzahl: anzahl.value})
    if (ergebnis) meldung.value = t('generator.erzeugt', {anzahl: (ergebnis.szenarioIds as string[]).length})
}

async function automatisch(an: boolean): Promise<void> {
    await senden('engine.parameter', {parameter: {autoGenerieren: an}})
}
</script>

<template>
    <details class="rounded border border-rand p-3">
        <summary class="cursor-pointer text-sm font-bold">{{ t('generator.titel') }}</summary>
        <div class="mt-2 flex flex-col gap-2">
            <div class="grid grid-cols-3 gap-2">
                <label v-for="gewicht in GEWICHTE" :key="gewicht.feld" :class="BESCHRIFTUNG">{{ t(gewicht.schluessel) }}
                    <input v-model.number="einstellung[gewicht.feld]" type="number" min="0" max="100" :class="FELD" @change="einstellen"/>
                </label>
            </div>
            <label :class="BESCHRIFTUNG">{{ t('generator.kategorie') }}
                <input v-model="einstellung.kategorie" :placeholder="t('generator.kategorieHinweis')" :class="FELD" @change="einstellen"/>
            </label>
            <GebietWahl :model-value="{bezirk: einstellung.bezirk, ortsteil: einstellung.ortsteil}" @update:model-value="gebietSetzen"/>
            <label class="flex items-center gap-2 text-sm">
                <input :checked="autoGenerieren" type="checkbox" @change="automatisch(($event.target as HTMLInputElement).checked)"/>{{ t('generator.automatisch') }}
            </label>
            <div class="flex items-end gap-2">
                <label :class="BESCHRIFTUNG">{{ t('generator.anzahl') }}<input v-model.number="anzahl" type="number" min="1" max="20" :class="['w-20', FELD]"/></label>
                <button type="button" class="h-8 rounded bg-tinte px-3 text-sm font-semibold text-white" @click="generieren">{{ t('generator.los') }}</button>
            </div>
            <p v-if="meldung" :role="fehler ? 'alert' : 'status'" :class="['m-0 text-sm', fehler ? 'text-fehler' : 'text-ok']">{{ meldung }}</p>
        </div>
    </details>
</template>
