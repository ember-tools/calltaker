<script setup lang="ts">
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import {dauer, useUhr} from '../composables/useUhr'
import {aktuellerKnoten, endergebnis, fachrichtungImPfad, gewaehltesProtokoll, hoehereEndpunkte, unterscheidungen, zwischenergebnis, type Ergebnis} from '../modell/abfrageweg'
import type {Abfrageeintrag} from '../modell/eintraege'
import {einenZurueck, mitAutomatik, ordnen} from '../modell/eingrenzung'
import {leererFensterzustand, type Fensterzustand} from '../modell/fensterzustand'
import type {Uebergabebereitschaft} from '../modell/uebergabe'
import {GEFAHRENZAHL, type Warntafel} from '../modell/gefahrstoffe'
import {wertAusTafel} from '../modell/warntafel'
import type {Leitfrageneintrag} from '../modell/eintraege'
import {leitfragenAn, leitstand} from '../modell/leitfragen'
import LeitfragenSpalte from './LeitfragenSpalte.vue'
import SnaKacheln from './SnaKacheln.vue'
import WarntafelFeld from './WarntafelFeld.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, gesperrt: boolean, seit?: number, uebergabe?: Uebergabebereitschaft, uebergebenUm?: number, ruhig?: boolean}>()
const abfrage = defineModel<Abfrageeintrag>({required: true})
const leitfragen = defineModel<Leitfrageneintrag[]>('leitfragen', {default: () => []})
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
const fachrichtung = computed(() => fachrichtungImPfad(props.graph, abfrage.value.pfad))
const leitung = computed(() => (knoten.value?.antworten ? leitfragenAn(props.graph, stand.value.knoten) : undefined))
const leitAntworten = computed(() => [...ordnung.value.vorn, ...ordnung.value.weitere])
const leitStand = computed(() => (leitung.value ? leitstand(leitung.value, leitAntworten.value.map(a => a.id), leitfragen.value) : undefined))
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

/**
 * Puts the focus on the first tile or field of the question, so the trainee can type at once;
 * the guidance questions answer with Alt and a digit from anywhere and need no focus.
 */
function fokussieren(): void {
    const koerperElement = koerper.value
    const ziel = koerperElement?.querySelector<HTMLElement>('[data-antworten] button, [data-antworten] input')
        ?? koerperElement?.querySelector<HTMLElement>('form input, button')
    ziel?.focus()
}

watch(() => stand.value.knoten, () => void nextTick(fokussieren))

defineExpose({fokussieren})
</script>

<template>
    <section :aria-label="t('sna.titel')" class="flex min-w-0 flex-col overflow-hidden rounded-lg border border-default bg-default">
        <div role="toolbar" :aria-label="t('sna.werkzeuge')" class="flex flex-wrap items-center gap-2 border-b border-default bg-elevated px-3 py-2.5">
            <span class="flex h-10 items-center rounded bg-inverted px-3 font-mono text-inverted">{{ dauer(jetzt - (seit ?? jetzt)) }}</span>
            <UButton color="neutral" variant="outline" size="lg" :disabled="abfrage.pfad.length === 0 && !abfrage.aufwertung && !abfrage.abbruch" @click="zurueck">{{ t('sna.zurueck') }}</UButton>
            <UButton color="neutral" variant="outline" size="lg" @click="umschalten('hilfe')">{{ t('sna.ersteHilfe') }}</UButton>
            <UButton color="neutral" variant="outline" size="lg" :disabled="!protokoll || Boolean(ende && !abfrage.abbruch && !abfrage.aufwertung && hoeher.length === 0)" @click="umschalten('aufwertung')">{{ t('sna.aufwertung') }}</UButton>
            <UButton v-if="uebergabe" size="lg" :disabled="uebergabe === 'gesperrt' || uebergabe === 'erfolgt'" :color="uebergabe === 'faellig' ? 'warning' : uebergabe === 'erfolgt' ? 'success' : 'neutral'" :variant="uebergabe === 'faellig' ? 'solid' : uebergabe === 'erfolgt' ? 'soft' : 'outline'" @click="emit('uebergeben')">
                <UIcon :name="uebergabe === 'erfolgt' ? 'i-lucide-check' : 'i-lucide-share'" class="mr-1.5" aria-hidden="true"/>
                {{ uebergabe === 'erfolgt' ? t('uebergabe.erfolgt', {dauer: dauer((uebergebenUm ?? jetzt) - (seit ?? uebergebenUm ?? jetzt))}) : t('uebergabe.knopf') }}
            </UButton>
            <span v-if="uebergabe === 'faellig'" role="status" class="text-sm font-semibold text-warning">{{ t('uebergabe.jetzt') }}</span>
            <UButton class="ml-auto" size="lg" color="error" variant="outline" :disabled="Boolean(ende) || !zwischen" @click="umschalten('abbruch')">{{ t('sna.abbruch') }}</UButton>
        </div>
        <div class="flex flex-wrap items-center gap-3 border-b border-warning/40 bg-warning/10 px-4 py-2 text-sm">
            <span class="font-bold text-warning">{{ t('sna.zwischenergebnis') }}</span>
            <template v-if="zwischen">
                <span class="font-mono font-semibold">{{ protokoll?.label ?? '' }} · {{ zwischen.code }}</span>
                <span class="rounded border border-warning/60 bg-default px-2 font-mono">{{ zwischen.kategorie }}</span>
            </template>
            <span v-else class="text-warning">{{ t('sna.offen') }}</span>
        </div>
        <div v-if="offen" class="border-b border-default bg-default px-4 py-3 text-sm">
            <p v-if="offen === 'hilfe'" class="m-0">{{ knoten?.hinweis ?? t('sna.keineHinweise') }}</p>
            <div v-else-if="offen === 'aufwertung'" class="flex flex-col gap-1">
                <span class="font-semibold">{{ t('sna.aufwertungTitel') }}</span>
                <span v-if="hoeher.length === 0" class="text-muted">{{ t('sna.keineAufwertung') }}</span>
                <UButton v-for="ziel in hoeher" :key="ziel.knoten" color="neutral" variant="outline" size="sm" @click="aufwerten(ziel.knoten, ziel.code)">{{ ziel.code }} · {{ ziel.kategorie }} · {{ ziel.anlass }}</UButton>
            </div>
            <form v-else class="flex flex-wrap items-end gap-2" @submit.prevent="abbrechen">
                <label class="flex flex-1 flex-col gap-1 text-xs font-semibold text-muted">
                    {{ t('sna.abbruchGrund') }}
                    <input v-model="grund" required class="native-field"/>
                </label>
                <UButton color="error" size="sm" type="submit">{{ t('sna.abbruchBestaetigen') }}</UButton>
                <UButton color="neutral" variant="outline" size="sm" @click="offen = null">{{ t('sna.schliessen') }}</UButton>
            </form>
        </div>
        <div ref="koerper" class="flex flex-col gap-3 px-6 py-5">
            <template v-if="gesperrt && abfrage.pfad.length === 0 && !trotzdem">
                <p class="m-0 text-muted">{{ t('sna.erstOrt') }}</p>
                <UButton color="neutral" variant="outline" size="sm" class="self-start" @click="beginnen">{{ t('sna.trotzdem') }}</UButton>
            </template>
            <template v-else-if="ende">
                <p class="m-0 text-lg font-semibold text-success">{{ abfrage.aufwertung ? t('sna.aufgewertet', {code: ende.code}) : t('sna.fertig', {code: `${ende.code} · ${ende.kategorie}`}) }}</p>
                <p v-if="abfrage.abbruch" class="m-0 text-sm text-muted">{{ t('sna.abgebrochen', {grund: abfrage.abbruch.grund}) }}</p>
            </template>
            <template v-else-if="knoten">
                <h3 class="m-0 text-2xl font-semibold text-highlighted">{{ knoten.frage }} <i v-if="knoten.hinweis" class="font-medium text-info">[{{ knoten.hinweis }}]</i></h3>
                <div v-if="knoten.antworten" class="flex flex-col gap-4">
                    <LeitfragenSpalte v-if="leitung && leitStand" v-model="leitfragen" :eintrag="leitung" :antworten="leitAntworten" :stand="leitStand" :ruhig="ruhig" @sofort="emit('sofort')" @waehlen="antwort => schritt({antwort})"/>
                    <SnaKacheln v-model:suche="kachelsuche" v-model:weitere-offen="weitereOffen" data-antworten :antworten="ordnung.vorn" :weitere="ordnung.weitere" :zusaetze="zusaetze" :farbe="fachrichtung" :passend="leitStand?.beantwortet.length ? leitStand.kacheln : undefined" :vorgeschlagen="leitStand?.vorschlag" @waehlen="antwort => schritt({antwort})"/>
                </div>
                <form v-else-if="knoten.eingabe?.art === 'warntafel'" class="flex flex-col gap-2" @submit.prevent="schritt({wert: wertAusTafel(tafel)})">
                    <WarntafelFeld v-model="tafel"/>
                    <div class="flex flex-wrap gap-2">
                        <UButton type="submit" :disabled="!tafelGueltig">{{ t('sna.weiter') }}</UButton>
                        <UButton v-if="knoten.eingabe.leer" color="neutral" variant="outline" @click="schritt({})">{{ knoten.eingabe.leer.label }}</UButton>
                    </div>
                </form>
                <form v-else-if="knoten.eingabe" class="flex flex-wrap items-end gap-2" @submit.prevent="schritt({wert: wert.trim()})">
                    <label class="flex flex-1 flex-col gap-1 text-xs font-semibold text-muted">
                        {{ knoten.eingabe.platzhalter }}
                        <input v-model="wert" class="native-field"/>
                    </label>
                    <UButton type="submit" :disabled="!wert.trim()">{{ t('sna.weiter') }}</UButton>
                    <UButton v-if="knoten.eingabe.leer" color="neutral" variant="outline" @click="schritt({})">{{ knoten.eingabe.leer.label }}</UButton>
                </form>
            </template>
            <details v-if="abfrage.pfad.length" class="rounded border border-default">
                <summary class="cursor-pointer px-3 py-2 text-sm font-semibold">{{ t('sna.pfad', {anzahl: abfrage.pfad.length}) }}</summary>
                <ol class="m-0 py-1 pl-9 pr-3 text-sm leading-relaxed">
                    <li v-for="(zeile, stelle) in pfadText" :key="stelle">{{ zeile }}</li>
                </ol>
            </details>
        </div>
    </section>
</template>
