<script setup lang="ts">
import {computed, ref} from 'vue'
import {FELD} from './formular'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph, Endpunkt} from '../modell/abfragegraph'
import {aktuellerKnoten, unterscheidungen, type Ergebnis} from '../modell/abfrageweg'
import type {Schritteintrag} from '../modell/eintraege'
import {antwortenAusPfad, pfadAusAntworten, pfadZumEndpunkt, zielAusPfad} from '../modell/szenarioentwurf'
import type {Befund, Wahl, Ziel} from '../modell/szenario'
import PfadSuche from './PfadSuche.vue'
import SnaKacheln from './SnaKacheln.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, befunde: Befund[]}>()
const antworten = defineModel<Record<string, Wahl>>('antworten', {required: true})
const ziel = defineModel<Ziel | undefined>('ziel', {required: true})

const {t} = useI18n()
const wert = ref('')

const pfad = computed(() => pfadAusAntworten(props.graph, antworten.value))
const stand = computed(() => aktuellerKnoten(props.graph, pfad.value))
const knoten = computed(() => props.graph.knoten[stand.value.knoten])
const erreicht = computed(() => zielAusPfad(props.graph, pfad.value))
const zielBefunde = computed(() => (ziel.value ? befundeNach.value.get(ziel.value.knoten) ?? [] : []))
const zielStimmt = computed(() => Boolean(erreicht.value && ziel.value && erreicht.value.knoten === ziel.value.knoten))
const zusaetze = computed(() => (knoten.value ? unterscheidungen(knoten.value, props.schwerste, props.graph) : new Map<string, string>()))
const ausserhalb = computed(() => Object.keys(antworten.value).filter(id => !pfad.value.some(s => s.knoten === id)))
const befundeNach = computed(() => {
    const nach = new Map<string, Befund[]>()
    for (const befund of props.befunde) nach.set(befund.knoten ?? '', [...(nach.get(befund.knoten ?? '') ?? []), befund])
    return nach
})
const zeilen = computed(() => pfad.value.map((schritt, stelle) => ({
    stelle,
    knoten: schritt.knoten,
    frage: props.graph.knoten[schritt.knoten]?.frage ?? schritt.knoten,
    antwort: props.graph.knoten[schritt.knoten]?.antworten?.find(a => a.id === schritt.antwort)?.label ?? schritt.wert ?? t('editor.leer'),
    befunde: befundeNach.value.get(schritt.knoten) ?? [],
})))

function setzen(neu: Schritteintrag[]): void {
    antworten.value = antwortenAusPfad(props.graph, neu, antworten.value)
    ziel.value = zielAusPfad(props.graph, neu)
    wert.value = ''
}

function schritt(eintrag: {antwort?: string, wert?: string}): void {
    setzen([...pfad.value, {knoten: stand.value.knoten, ...eintrag}])
}

function eingeben(): void {
    schritt(wert.value.trim() ? {wert: wert.value.trim()} : {})
}

/**
 * The look of a path row: red for an error, amber for a warning.
 *
 * @param befunde the row's findings
 * @returns the classes
 */
function zeilenKlasse(befunde: Befund[]): string {
    if (befunde.some(b => b.art === 'fehler')) return 'border-error bg-error/10'
    return befunde.length ? 'border-warning bg-warning/10' : 'border-default'
}

function abHier(stelle: number): void {
    setzen(pfad.value.slice(0, stelle))
}

function springen(endpunkt: Endpunkt): void {
    setzen(pfadZumEndpunkt(props.graph, pfad.value, endpunkt))
}

function ausserhalbEntfernen(): void {
    setzen(pfad.value)
}
</script>

<template>
    <div class="flex flex-col gap-3">
        <PfadSuche :graph="graph" @endpunkt="springen"/>
        <ol class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
            <li v-for="zeile in zeilen" :key="zeile.knoten" :class="['flex items-start gap-2 rounded border px-2 py-1', zeilenKlasse(zeile.befunde)]">
                <span class="flex-1"><span class="text-muted">{{ zeile.frage }}</span> · <b>{{ zeile.antwort }}</b>
                    <span v-for="befund in zeile.befunde" :key="befund.meldung" :class="['block text-xs', befund.art === 'fehler' ? 'text-error' : 'text-warning']">{{ befund.meldung }}</span>
                </span>
                <UButton color="neutral" variant="link" size="xs" :aria-label="t('editor.abHierNeu', {frage: zeile.frage})" @click="abHier(zeile.stelle)">{{ t('editor.aendern') }}</UButton>
            </li>
        </ol>
        <p v-if="ziel" :class="['m-0 rounded px-2 py-1 text-sm font-semibold', zielStimmt && !zielBefunde.length ? 'bg-success/10' : 'bg-error/10 text-error']" role="status">
            {{ t('editor.ziel', {code: ziel.code, kategorie: graph.knoten[ziel.knoten]?.kategorie ?? ''}) }}
            <span v-if="!erreicht" class="block text-xs">{{ t('editor.zielNichtErreicht') }}</span>
            <span v-else-if="!zielStimmt" class="block text-xs">{{ t('editor.zielAnders', {code: erreicht.code}) }}</span>
            <span v-for="befund in zielBefunde" :key="befund.meldung" class="block text-xs">{{ befund.meldung }}</span>
        </p>
        <template v-if="!erreicht && knoten">
            <p class="m-0 text-sm font-semibold">{{ knoten.frage }}</p>
            <SnaKacheln v-if="knoten.antworten" :antworten="knoten.antworten" :zusaetze="zusaetze" @waehlen="antwort => schritt({antwort})"/>
            <div v-else-if="knoten.eingabe" class="flex gap-2">
                <input v-model="wert" :aria-label="knoten.frage" :placeholder="knoten.eingabe.platzhalter" :class="['flex-1', FELD]" @keydown.enter.prevent="eingeben"/>
                <UButton color="neutral" variant="outline" size="sm" @click="eingeben">{{ t('editor.weiter') }}</UButton>
            </div>
        </template>
        <div v-if="ausserhalb.length" class="flex flex-col gap-1 rounded border border-warning p-2 text-sm" role="alert">
            <p class="m-0">{{ t('editor.ausserhalb', {anzahl: ausserhalb.length}) }}</p>
            <ul class="m-0 pl-5 text-xs">
                <li v-for="id in ausserhalb" :key="id">{{ graph.knoten[id]?.frage ?? id }}<span v-for="befund in befundeNach.get(id) ?? []" :key="befund.meldung" class="text-error"> · {{ befund.meldung }}</span></li>
            </ul>
            <UButton color="neutral" variant="link" size="xs" class="self-start" @click="ausserhalbEntfernen">{{ t('editor.ausserhalbEntfernen') }}</UButton>
        </div>
    </div>
</template>
