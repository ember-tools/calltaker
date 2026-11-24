<script setup lang="ts">
import {faCheck, faShareFromSquare} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import {dauer, useUhr} from '../composables/useUhr'
import {aktuellerKnoten, endergebnis, gewaehltesProtokoll, hoehereEndpunkte, unterscheidungen, zwischenergebnis, type Ergebnis} from '../modell/abfrageweg'
import type {Abfrageeintrag} from '../modell/eintraege'
import {einenZurueck, mitAutomatik, ordnen} from '../modell/eingrenzung'
import {leererFensterzustand, type Fensterzustand} from '../modell/fensterzustand'
import type {Uebergabebereitschaft} from '../modell/uebergabe'
import {GEFAHRENZAHL, type Warntafel} from '../modell/gefahrstoffe'
import {wertAusTafel} from '../modell/warntafel'
import SnaKacheln from './SnaKacheln.vue'
import WarntafelFeld from './WarntafelFeld.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, gesperrt: boolean, seit?: number, uebergabe?: Uebergabebereitschaft, uebergebenUm?: number}>()
const abfrage = defineModel<Abfrageeintrag>({required: true})
const emit = defineEmits<{sofort: [], uebergeben: []}>()

const {t} = useI18n()
const jetzt = useUhr()
const ui = defineModel<Fensterzustand>('ui', {default: leererFensterzustand})

/**
 * A field of the window's state that templates can bind to.
 *
 * @param feld the field
 * @returns its value, written back as a new state
 */
function feld<K extends keyof Fensterzustand>(feld: K) {
    return computed<Fensterzustand[K]>({get: () => ui.value[feld], set: wert => {
        ui.value = {...ui.value, [feld]: wert}
    }})
}

const offen = feld('offen')
const grund = feld('grund')
const wert = feld('wert')
const trotzdem = feld('trotzdem')
const kachelsuche = feld('kachelsuche')
const weitereOffen = feld('weitere')

const stand = computed(() => aktuellerKnoten(props.graph, abfrage.value.pfad))
const knoten = computed(() => props.graph.knoten[stand.value.knoten])
const ordnung = computed(() => ordnen(props.graph, stand.value.knoten, abfrage.value.pfad))
const ende = computed(() => endergebnis(props.graph, abfrage.value))
const zwischen = computed(() => zwischenergebnis(props.graph, abfrage.value, props.schwerste))
const protokoll = computed(() => gewaehltesProtokoll(props.graph, abfrage.value.pfad))
const fachrichtung = computed(() => abfrage.value.pfad.find(s => s.knoten === props.graph.meta.wurzel)?.antwort)
const zusaetze = computed(() => (knoten.value ? unterscheidungen(knoten.value, props.schwerste, props.graph) : new Map<string, string>()))
const hoeher = computed(() => (protokoll.value?.protokoll ? hoehereEndpunkte(props.graph, protokoll.value.protokoll, zwischen.value?.kategorie ?? '', zwischen.value?.code) : []))
const pfadText = computed(() => abfrage.value.pfad.map(schritt => {
    const antwort = props.graph.knoten[schritt.knoten]?.antworten?.find(a => a.id === schritt.antwort)
    const text = `${props.graph.knoten[schritt.knoten]?.frage ?? schritt.knoten}: ${antwort?.label ?? schritt.wert ?? ''}`
    return schritt.automatisch ? `${text} ${t('sna.automatisch')}` : text
}))

const tafel = ref<Warntafel>({un: '', gefahrenzahl: ''})
const tafelGueltig = computed(() => /^\d{4}$/.test(tafel.value.un) && (!tafel.value.gefahrenzahl || GEFAHRENZAHL.test(tafel.value.gefahrenzahl)))

function schritt(eintrag: {antwort?: string, wert?: string}): void {
    tafel.value = {un: '', gefahrenzahl: ''}
    const pfad = [...abfrage.value.pfad.slice(0, stand.value.passend), {knoten: stand.value.knoten, ...eintrag}]
    abfrage.value = {...abfrage.value, pfad: mitAutomatik(props.graph, pfad)}
    wert.value = ''
    offen.value = null
    emit('sofort')
}

function zurueck(): void {
    const {aufwertung, abbruch, pfad} = abfrage.value
    abfrage.value = aufwertung || abbruch ? {pfad} : {pfad: einenZurueck(pfad)}
    emit('sofort')
}

function aufwerten(knotenId: string, code: string): void {
    abfrage.value = {...abfrage.value, aufwertung: {knoten: knotenId, code}}
    offen.value = null
    emit('sofort')
}

function abbrechen(): void {
    if (!grund.value.trim()) return
    const ergebnis = zwischen.value ? {knoten: zwischen.value.knoten, code: zwischen.value.code} : undefined
    abfrage.value = {...abfrage.value, abbruch: {grund: grund.value.trim(), ergebnis}}
    offen.value = null
    emit('sofort')
}

function umschalten(was: 'hilfe' | 'aufwertung' | 'abbruch'): void {
    offen.value = offen.value === was ? null : was
}

const koerper = ref<HTMLElement | null>(null)

function beginnen(): void {
    trotzdem.value = true
    void nextTick(fokussieren)
}

/** Puts the focus on the first tile or field of the question, so the trainee can type at once. */
function fokussieren(): void {
    koerper.value?.querySelector<HTMLElement>('[data-antworten] button, [data-antworten] input, form input, button')?.focus()
}

watch(() => stand.value.knoten, () => void nextTick(fokussieren))

defineExpose({fokussieren})
</script>

<template>
    <section :aria-label="t('sna.titel')" class="flex min-w-0 flex-col overflow-hidden rounded-lg border border-rand bg-flaeche">
        <div role="toolbar" :aria-label="t('sna.werkzeuge')" class="flex flex-wrap items-center gap-2 border-b border-rand bg-slate-100 px-3 py-2.5">
            <span class="flex h-10 items-center rounded bg-leiste px-3 font-mono text-white">{{ dauer(jetzt - (seit ?? jetzt)) }}</span>
            <button type="button" class="h-10 rounded border border-slate-400 bg-white px-3 text-sm font-semibold" :disabled="abfrage.pfad.length === 0 && !abfrage.aufwertung && !abfrage.abbruch" @click="zurueck">{{ t('sna.zurueck') }}</button>
            <button type="button" class="h-10 rounded border border-slate-400 bg-white px-3 text-sm font-semibold" @click="umschalten('hilfe')">{{ t('sna.ersteHilfe') }}</button>
            <button type="button" class="h-10 rounded border border-slate-400 bg-white px-3 text-sm font-semibold" :disabled="!protokoll || Boolean(ende && !abfrage.abbruch && !abfrage.aufwertung && hoeher.length === 0)" @click="umschalten('aufwertung')">{{ t('sna.aufwertung') }}</button>
            <button v-if="uebergabe" type="button" :disabled="uebergabe === 'gesperrt' || uebergabe === 'erfolgt'" :class="['h-10 rounded border px-3 text-sm font-semibold', uebergabe === 'faellig' ? 'border-amber-500 bg-amber-300 text-amber-950' : uebergabe === 'erfolgt' ? 'border-green-600 bg-green-50 text-ok' : 'border-slate-400 bg-white']" @click="emit('uebergeben')">
                <FontAwesomeIcon :icon="uebergabe === 'erfolgt' ? faCheck : faShareFromSquare" class="mr-1.5" aria-hidden="true"/>
                {{ uebergabe === 'erfolgt' ? t('uebergabe.erfolgt', {dauer: dauer((uebergebenUm ?? jetzt) - (seit ?? uebergebenUm ?? jetzt))}) : t('uebergabe.knopf') }}
            </button>
            <span v-if="uebergabe === 'faellig'" role="status" class="text-sm font-semibold text-amber-900">{{ t('uebergabe.jetzt') }}</span>
            <button type="button" class="ml-auto h-10 rounded border border-red-300 bg-white px-3 text-sm font-semibold text-red-800" :disabled="Boolean(ende) || !zwischen" @click="umschalten('abbruch')">{{ t('sna.abbruch') }}</button>
        </div>
        <div class="flex flex-wrap items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm">
            <span class="font-bold text-amber-900">{{ t('sna.zwischenergebnis') }}</span>
            <template v-if="zwischen">
                <span class="font-mono font-semibold">{{ protokoll?.label ?? '' }} · {{ zwischen.code }}</span>
                <span class="rounded border border-amber-400 bg-white px-2 font-mono">{{ zwischen.kategorie }}</span>
            </template>
            <span v-else class="text-amber-900">{{ t('sna.offen') }}</span>
        </div>
        <div v-if="offen" class="border-b border-rand bg-white px-4 py-3 text-sm">
            <p v-if="offen === 'hilfe'" class="m-0">{{ knoten?.hinweis ?? t('sna.keineHinweise') }}</p>
            <div v-else-if="offen === 'aufwertung'" class="flex flex-col gap-1">
                <span class="font-semibold">{{ t('sna.aufwertungTitel') }}</span>
                <span v-if="hoeher.length === 0" class="text-gedaempft">{{ t('sna.keineAufwertung') }}</span>
                <button v-for="ziel in hoeher" :key="ziel.knoten" type="button" class="rounded border border-slate-300 px-2 py-1 text-left font-mono" @click="aufwerten(ziel.knoten, ziel.code)">{{ ziel.code }} · {{ ziel.kategorie }} · {{ ziel.anlass }}</button>
            </div>
            <form v-else class="flex flex-wrap items-end gap-2" @submit.prevent="abbrechen">
                <label class="flex flex-1 flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('sna.abbruchGrund') }}
                    <input v-model="grund" required class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
                </label>
                <button type="submit" class="h-8 rounded bg-red-700 px-3 text-sm font-semibold text-white">{{ t('sna.abbruchBestaetigen') }}</button>
                <button type="button" class="h-8 rounded border border-slate-400 px-3 text-sm" @click="offen = null">{{ t('sna.schliessen') }}</button>
            </form>
        </div>
        <div ref="koerper" class="flex flex-col gap-3 px-6 py-5">
            <template v-if="gesperrt && abfrage.pfad.length === 0 && !trotzdem">
                <p class="m-0 text-gedaempft">{{ t('sna.erstOrt') }}</p>
                <button type="button" class="self-start rounded border border-slate-400 px-3 py-1.5 text-sm font-semibold" @click="beginnen">{{ t('sna.trotzdem') }}</button>
            </template>
            <template v-else-if="ende">
                <p class="m-0 text-lg font-semibold text-ok">{{ abfrage.aufwertung ? t('sna.aufgewertet', {code: ende.code}) : t('sna.fertig', {code: `${ende.code} · ${ende.kategorie}`}) }}</p>
                <p v-if="abfrage.abbruch" class="m-0 text-sm text-gedaempft">{{ t('sna.abgebrochen', {grund: abfrage.abbruch.grund}) }}</p>
            </template>
            <template v-else-if="knoten">
                <h3 class="m-0 text-2xl font-semibold text-sky-950">{{ knoten.frage }} <i v-if="knoten.hinweis" class="font-medium text-akzent">[{{ knoten.hinweis }}]</i></h3>
                <SnaKacheln v-if="knoten.antworten" v-model:suche="kachelsuche" v-model:weitere-offen="weitereOffen" data-antworten :antworten="ordnung.vorn" :weitere="ordnung.weitere" :zusaetze="zusaetze" :farbe="fachrichtung" @waehlen="antwort => schritt({antwort})"/>
                <form v-else-if="knoten.eingabe?.art === 'warntafel'" class="flex flex-col gap-2" @submit.prevent="schritt({wert: wertAusTafel(tafel)})">
                    <WarntafelFeld v-model="tafel"/>
                    <div class="flex flex-wrap gap-2">
                        <button type="submit" class="h-9 rounded bg-akzent px-4 font-semibold text-white" :disabled="!tafelGueltig">{{ t('sna.weiter') }}</button>
                        <button v-if="knoten.eingabe.leer" type="button" class="h-9 rounded border border-slate-400 px-3 text-sm" @click="schritt({})">{{ knoten.eingabe.leer.label }}</button>
                    </div>
                </form>
                <form v-else-if="knoten.eingabe" class="flex flex-wrap items-end gap-2" @submit.prevent="schritt({wert: wert.trim()})">
                    <label class="flex flex-1 flex-col gap-1 text-xs font-semibold text-gedaempft">
                        {{ knoten.eingabe.platzhalter }}
                        <input v-model="wert" class="h-9 rounded border border-slate-400 px-2 text-base text-tinte"/>
                    </label>
                    <button type="submit" class="h-9 rounded bg-akzent px-4 font-semibold text-white" :disabled="!wert.trim()">{{ t('sna.weiter') }}</button>
                    <button v-if="knoten.eingabe.leer" type="button" class="h-9 rounded border border-slate-400 px-3 text-sm" @click="schritt({})">{{ knoten.eingabe.leer.label }}</button>
                </form>
            </template>
            <details v-if="abfrage.pfad.length" class="rounded border border-rand">
                <summary class="cursor-pointer px-3 py-2 text-sm font-semibold">{{ t('sna.pfad', {anzahl: abfrage.pfad.length}) }}</summary>
                <ol class="m-0 py-1 pl-9 pr-3 text-sm leading-relaxed">
                    <li v-for="(zeile, stelle) in pfadText" :key="stelle">{{ zeile }}</li>
                </ol>
            </details>
        </div>
    </section>
</template>
