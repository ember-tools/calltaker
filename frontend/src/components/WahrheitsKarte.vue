<script setup lang="ts">
import {faCheck, faComments, faTruckMedical, faXmark} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import {mitKorrektur} from '../modell/eintraege'
import {dauer, useUhr} from '../composables/useUhr'
import {anzeigen} from '../modell/rufnummer'
import {leitfaden} from '../modell/leitfaden'
import {antwortAusLoesung, leitfragenAn, leitstand} from '../modell/leitfragen'
import {aktuellerKnoten} from '../modell/abfrageweg'
import {nachtraege} from '../modell/uebergabe'
import {tafelDerWahrheit} from '../modell/warntafel'
import {sichtVon, type Anruf} from '../modell/uebung'
import {vergleichePfad} from '../modell/wahrheitspfad'
import {bewerten} from '../phasen/register'
import {reanimationBewerten, STANDARDZIELE, uebergabeBewerten, type Zielzeiten} from '../phasen/zeitbewertung'
import {zeile} from '../phasen/standort'
import type {Urteil} from '../phasen/typen'
import PfadVergleichListe from './PfadVergleichListe.vue'
import WarntafelAnzeige from './WarntafelAnzeige.vue'

const props = defineProps<{graph: Abfragegraph, anruf: Anruf, ziele?: Zielzeiten}>()
const emit = defineEmits<{korrigieren: [anleitung: string, gegeben: boolean], eintreffen: []}>()

const {t} = useI18n()
const szenario = computed(() => props.anruf.szenario)
const ziel = computed(() => props.graph.knoten[szenario.value.ziel.knoten])
const vergleich = computed(() => vergleichePfad(props.graph, szenario.value.antworten, props.anruf.eintraege.abfrage.pfad))
const bewertungen = computed(() => {
    const sicht = sichtVon(props.anruf)
    const ziele = props.ziele ?? STANDARDZIELE
    return [
        ...bewerten(mitKorrektur(props.anruf.eintraege, props.anruf.korrektur), szenario.value, props.graph).flatMap(p => p.bewertungen),
        ...reanimationBewerten(props.graph, sicht, szenario.value, ziele),
        ...(props.anruf.zustand === 'beendet' || props.anruf.eintraege.zeiten.uebergabe ? uebergabeBewerten(props.graph, sicht, szenario.value, ziele) : []),
    ]
})
const adresse = computed(() => zeile(szenario.value.ort.adresse))
const rolle = computed(() => {
    const {stimmung, sprache} = szenario.value.rolle
    return [stimmung ? t('wahrheit.stimmung', {stimmung: t(`editor.stimmungen.${stimmung}`)}) : '', sprache ? t('wahrheit.sprache', {sprache}) : ''].filter(Boolean).join(' · ')
})
const ortsangaben = computed(() => (['objekt', 'geschoss', 'klingel', 'anfahrt', 'gefahren', 'haustier'] as const)
    .filter(feld => szenario.value.ort[feld])
    .map(feld => ({feld, wert: szenario.value.ort[feld]})))
const nachgetragen = computed(() => [...nachtraege(props.graph, props.anruf.eintraege)].map(teil => t(`uebergabe.teil.${teil}`)))
const jetztUhr = useUhr()
const tafel = computed(() => tafelDerWahrheit(props.graph, szenario.value.antworten))
const stichpunkte = computed(() => leitfaden(props.graph, szenario.value))
const jetzt = computed(() => {
    const hier = vergleich.value.schritte.find(schritt => schritt.stand === 'hier')
    if (hier?.knoten === props.graph.meta.wurzel) return {frage: hier.frage, soll: t('leitfaden.wurzel')}
    return hier ? {frage: hier.frage, soll: hier.soll} : vergleich.value.abseits
})
const leitfrage = computed(() => {
    const eintraege = props.anruf.eintraege
    const knotenId = aktuellerKnoten(props.graph, eintraege.abfrage.pfad).knoten
    const eintrag = leitfragenAn(props.graph, knotenId)
    const kacheln = (props.graph.knoten[knotenId]?.antworten ?? []).map(antwort => antwort.id)
    if (!eintrag || props.anruf.zustand === 'beendet') return undefined
    const stand = leitstand(eintrag, kacheln, eintraege.leitfragen ?? [])
    if (!stand.frage) return undefined
    return {frage: stand.frage.frage, antworten: antwortAusLoesung(eintrag, stand.frage, stand.kacheln, szenario.value.antworten)}
})
const erreichbar = computed(() => {
    const anrufer = szenario.value.anrufer
    return anrufer.rueckrufnummer && anrufer.rueckrufnummer !== anrufer.rufnummer ? anzeigen(anrufer.rueckrufnummer) : ''
})

const URTEIL: Record<Urteil, string> = {richtig: 'text-ok', teilweise: 'text-warnung', falsch: 'font-semibold text-fehler', offen: 'text-gedaempft', hinweis: ''}
</script>

<template>
    <section :aria-label="t('wahrheit.titel')" class="flex flex-col gap-3 rounded-lg border border-rand bg-flaeche p-4 text-sm">
        <header class="flex flex-col gap-1">
            <h2 class="m-0 text-base font-bold">{{ szenario.titel }}</h2>
            <p class="m-0"><b class="font-mono">{{ szenario.ziel.code }}</b> · {{ ziel?.kategorie }} · {{ ziel?.anlass }}</p>
            <p v-if="rolle" class="m-0">{{ rolle }}</p>
            <div v-if="anruf.zustand === 'beendet' && (szenario.rolle.notizen || szenario.rolle.beschwerden?.length)" class="m-0 flex flex-col gap-1 rounded bg-amber-50 p-2">
                <p v-if="szenario.rolle.notizen" class="m-0 whitespace-pre-line">{{ szenario.rolle.notizen }}</p>
                <ul v-if="szenario.rolle.beschwerden?.length" :aria-label="t('wahrheit.beschwerden')" class="m-0 pl-5">
                    <li v-for="(beschwerde, nummer) in szenario.rolle.beschwerden" :key="nummer">{{ beschwerde }}</li>
                </ul>
            </div>
            <section v-if="anruf.zustand !== 'beendet'" :aria-label="t('leitfaden.titel')" class="flex flex-col gap-1 rounded border border-sky-200 bg-sky-50 p-2">
                <h3 class="m-0 text-sm font-bold text-sky-900"><FontAwesomeIcon :icon="faComments" class="mr-1.5" aria-hidden="true"/>{{ t('leitfaden.titel') }}</h3>
                <ul class="m-0 flex flex-col gap-0.5 pl-5">
                    <li v-for="(punkt, nummer) in stichpunkte" :key="`${nummer}-${punkt.schluessel}`" class="whitespace-pre-line">{{ t(punkt.schluessel, punkt.werte ?? {}) }}</li>
                </ul>
                <p v-if="jetzt" class="m-0 rounded bg-amber-100 px-2 py-1" role="status">{{ t('leitfaden.jetzt', {frage: jetzt.frage}) }} <b>{{ jetzt.soll ?? t('wahrheit.improvisieren') }}</b></p>
                <p v-if="leitfrage" class="m-0 rounded bg-sky-100 px-2 py-1">{{ t('leitfragen.loesungFrage', {frage: leitfrage.frage}) }} <b>{{ leitfrage.antworten.length ? leitfrage.antworten.join(t('leitfragen.oder')) : t('leitfragen.frei') }}</b></p>
            </section>
            <p v-if="anruf.eintraege.zeiten.uebergabe" class="m-0 font-semibold text-ok">{{ t('uebergabe.erfolgt', {dauer: dauer(anruf.eintraege.zeiten.uebergabe - (anruf.angenommenUm ?? anruf.eintraege.zeiten.uebergabe))}) }}<span v-if="nachgetragen.length" class="font-normal text-akzent"> · {{ t('uebergabe.nachgetragen', {teile: nachgetragen.join(', ')}) }}</span></p>
            <p v-else-if="anruf.zustand === 'gespraech' || anruf.zustand === 'beendet'" class="m-0 text-gedaempft">{{ t('uebergabe.nicht') }}</p>
            <p v-if="anruf.eintreffenUm !== undefined" class="m-0 flex flex-wrap items-center gap-2">
                <FontAwesomeIcon :icon="faTruckMedical" aria-hidden="true"/>
                <span v-if="jetztUhr < anruf.eintreffenUm">{{ t('kraefte.unterwegs', {dauer: dauer(anruf.eintreffenUm - jetztUhr)}) }}</span>
                <span v-else class="font-semibold text-ok">{{ t('kraefte.eingetroffen') }}</span>
                <button v-if="anruf.zustand === 'gespraech' && jetztUhr < anruf.eintreffenUm" type="button" class="rounded border border-slate-400 px-2 py-0.5 text-xs font-semibold" @click="emit('eintreffen')">{{ t('kraefte.jetzt') }}</button>
            </p>
        </header>
        <dl class="m-0 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
            <dt class="text-gedaempft">{{ t('wahrheit.anrufer') }}</dt>
            <dd class="m-0">{{ szenario.anrufer.name }} · {{ szenario.anrufer.rufnummerUnterdrueckt ? t('wahrheit.unterdrueckt') : anzeigen(szenario.anrufer.rufnummer ?? '') }}<span v-if="erreichbar"> · {{ t('wahrheit.erreichbar', {nummer: erreichbar}) }}</span></dd>
            <template v-if="szenario.betroffener?.name">
                <dt class="text-gedaempft">{{ t('wahrheit.betroffener') }}</dt>
                <dd class="m-0">{{ szenario.betroffener.name }}</dd>
            </template>
            <dt class="text-gedaempft">{{ t('wahrheit.ort') }}</dt>
            <dd class="m-0">{{ adresse }}</dd>
            <template v-if="tafel">
                <dt class="text-gedaempft">{{ t('warntafel.titel') }}</dt>
                <dd class="m-0"><WarntafelAnzeige :tafel="tafel"/></dd>
            </template>
            <template v-for="angabe in ortsangaben" :key="angabe.feld">
                <dt class="text-gedaempft">{{ t(`maske.${angabe.feld}`) }}</dt>
                <dd class="m-0">{{ angabe.wert }}</dd>
            </template>
        </dl>
        <ul class="m-0 flex list-none flex-col gap-0.5 p-0" :aria-label="t('wahrheit.abgleich')">
            <li v-for="(bewertung, stelle) in bewertungen" :key="stelle" :class="['flex gap-2', URTEIL[bewertung.urteil]]">
                <span class="w-32 shrink-0">{{ bewertung.beschriftung ?? t(bewertung.feld) }}</span>
                <span v-if="bewertung.abstand !== undefined">{{ t('wahrheit.abstand', {meter: bewertung.abstand}) }}</span>
                <span v-else-if="bewertung.urteil === 'offen'">{{ t('wahrheit.offen') }}</span>
                <span v-else>{{ bewertung.ist }}<template v-if="bewertung.urteil === 'falsch' || bewertung.urteil === 'teilweise' || (bewertung.urteil === 'hinweis' && bewertung.soll)"> · {{ t('wahrheit.soll', {soll: bewertung.soll}) }}</template><template v-if="bewertung.stufe && bewertung.stufe !== 'exakt'"> ({{ t(`stufe.${bewertung.stufe}`) }})</template></span>
                <button v-if="bewertung.anleitung" type="button" class="ml-auto shrink-0 text-xs underline" @click="emit('korrigieren', bewertung.anleitung, !bewertung.gegeben)"><FontAwesomeIcon :icon="bewertung.gegeben ? faXmark : faCheck" class="mr-1" aria-hidden="true"/>{{ bewertung.gegeben ? t('wahrheit.nichtGegeben') : t('wahrheit.gegeben') }}</button>
            </li>
        </ul>
        <PfadVergleichListe :vergleich="vergleich" live/>
    </section>
</template>
