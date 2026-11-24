<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Gebiet} from '../api/gebiete'
import type {Abfragegraph} from '../modell/abfragegraph'
import {lagen} from '../modell/lagen'
import {BELASTENDE, type Belastend, type Erzeugung} from '../modell/uebung'
import {BESCHRIFTUNG, FELD} from './formular'
import GebietWahl from './GebietWahl.vue'

const props = defineProps<{
    erzeugung: Erzeugung
    autoGenerieren: boolean
    graph?: Abfragegraph
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()

const {t} = useI18n()
const GEWICHTE = [
    {feld: 'gewichtRd', schluessel: 'generator.rd'},
    {feld: 'gewichtBrand', schluessel: 'generator.brand'},
    {feld: 'gewichtTh', schluessel: 'generator.th'},
    {feld: 'anteilOrte', schluessel: 'generator.anteilOrte'},
    {feld: 'anteilOhneAdresse', schluessel: 'generator.anteilOhneAdresse'},
] as const
const anzahl = ref(5)
const gruppen = computed(() => (props.graph ? lagen(props.graph) : []))

/**
 * Limits made-up scenarios to one protocol, or lifts the limit; a category filter from before is
 * cleared with it.
 *
 * @param protokoll the protocol, or empty for all
 */
function lageSetzen(protokoll: string): void {
    einstellung.value = {...einstellung.value, protokoll, kategorie: ''}
    void einstellen()
}
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

/**
 * Allows or excludes one category of distressing situations.
 *
 * @param kategorie the category
 * @param erlaubt whether it may be drawn
 */
async function belastendSetzen(kategorie: Belastend, erlaubt: boolean): Promise<void> {
    const bisher = (einstellung.value.belastende ?? []).filter(k => k !== kategorie)
    einstellung.value = {...einstellung.value, belastende: erlaubt ? [...bisher, kategorie] : bisher}
    await einstellen()
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
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <label v-for="gewicht in GEWICHTE" :key="gewicht.feld" :class="[BESCHRIFTUNG, 'justify-between']">{{ t(gewicht.schluessel) }}
                    <input v-model.number="einstellung[gewicht.feld]" type="number" min="0" max="100" :class="FELD" @change="einstellen"/>
                </label>
            </div>
            <label :class="BESCHRIFTUNG">{{ t('generator.lage') }}
                <select :value="einstellung.protokoll" :class="FELD" @change="lageSetzen(($event.target as HTMLSelectElement).value)">
                    <option value="">{{ t('generator.alleLagen') }}</option>
                    <optgroup v-for="gruppe in gruppen" :key="gruppe.fachrichtung" :label="gruppe.name">
                        <option v-for="lage in gruppe.lagen" :key="lage.protokoll" :value="lage.protokoll">{{ t('generator.lageMitCodes', {name: lage.name, anzahl: lage.anzahl}) }}</option>
                    </optgroup>
                </select>
            </label>
            <fieldset class="m-0 flex flex-wrap gap-x-4 gap-y-1 rounded border border-rand p-2">
                <legend class="px-1 text-sm font-bold">{{ t('generator.belastende') }}</legend>
                <label v-for="kategorie in BELASTENDE" :key="kategorie" class="flex items-center gap-2 text-sm">
                    <input :checked="einstellung.belastende?.includes(kategorie)" type="checkbox" @change="belastendSetzen(kategorie, ($event.target as HTMLInputElement).checked)"/>{{ t(`generator.belastend.${kategorie}`) }}
                </label>
                <p class="m-0 w-full text-xs text-gedaempft">{{ t('generator.belastendeHinweis') }}</p>
            </fieldset>
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
