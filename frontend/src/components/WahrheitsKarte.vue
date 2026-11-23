<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import {anzeigen} from '../modell/rufnummer'
import type {Anruf} from '../modell/uebung'
import {vergleichePfad, type Schrittstand} from '../modell/wahrheitspfad'
import {bewerten} from '../phasen/register'
import {zeile} from '../phasen/standort'
import type {Urteil} from '../phasen/typen'

const props = defineProps<{graph: Abfragegraph, anruf: Anruf}>()

const {t} = useI18n()
const szenario = computed(() => props.anruf.szenario)
const ziel = computed(() => props.graph.knoten[szenario.value.ziel.knoten])
const vergleich = computed(() => vergleichePfad(props.graph, szenario.value.antworten, props.anruf.eintraege.abfrage.pfad))
const bewertungen = computed(() => bewerten(props.anruf.eintraege, szenario.value, props.graph).flatMap(p => p.bewertungen))
const adresse = computed(() => zeile(szenario.value.ort.adresse))
const rolle = computed(() => {
    const {stimmung, sprache} = szenario.value.rolle
    return [stimmung ? t('wahrheit.stimmung', {stimmung: t(`editor.stimmungen.${stimmung}`)}) : '', sprache ? t('wahrheit.sprache', {sprache}) : ''].filter(Boolean).join(' · ')
})
const ortsangaben = computed(() => (['objekt', 'geschoss', 'klingel', 'anfahrt', 'gefahren'] as const)
    .filter(feld => szenario.value.ort[feld])
    .map(feld => ({feld, wert: szenario.value.ort[feld]})))
const erreichbar = computed(() => {
    const anrufer = szenario.value.anrufer
    return anrufer.rueckrufnummer && anrufer.rueckrufnummer !== anrufer.rufnummer ? anzeigen(anrufer.rueckrufnummer) : ''
})

const SCHRITT: Record<Schrittstand, string> = {gleich: 'text-ok', anders: 'bg-red-50 text-fehler', offen: 'text-gedaempft', hier: 'bg-amber-100 font-bold'}
const URTEIL: Record<Urteil, string> = {richtig: 'text-ok', falsch: 'font-semibold text-fehler', offen: 'text-gedaempft'}
</script>

<template>
    <section :aria-label="t('wahrheit.titel')" class="flex flex-col gap-3 rounded-lg border border-rand bg-flaeche p-4 text-sm">
        <header class="flex flex-col gap-1">
            <h2 class="m-0 text-base font-bold">{{ szenario.titel }}</h2>
            <p class="m-0"><b class="font-mono">{{ szenario.ziel.code }}</b> · {{ ziel?.kategorie }} · {{ ziel?.anlass }}</p>
            <p v-if="rolle" class="m-0">{{ rolle }}</p>
            <p v-if="szenario.rolle.notizen" class="m-0 whitespace-pre-line rounded bg-amber-50 p-2">{{ szenario.rolle.notizen }}</p>
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
            <template v-for="angabe in ortsangaben" :key="angabe.feld">
                <dt class="text-gedaempft">{{ t(`maske.${angabe.feld}`) }}</dt>
                <dd class="m-0">{{ angabe.wert }}</dd>
            </template>
        </dl>
        <ul class="m-0 flex list-none flex-col gap-0.5 p-0" :aria-label="t('wahrheit.abgleich')">
            <li v-for="bewertung in bewertungen" :key="bewertung.feld" :class="['flex gap-2', URTEIL[bewertung.urteil]]">
                <span class="w-32 shrink-0">{{ t(bewertung.feld) }}</span>
                <span v-if="bewertung.abstand !== undefined">{{ t('wahrheit.abstand', {meter: bewertung.abstand}) }}</span>
                <span v-else-if="bewertung.urteil === 'offen'">{{ t('wahrheit.offen') }}</span>
                <span v-else>{{ bewertung.ist }}<template v-if="bewertung.urteil === 'falsch'"> · {{ t('wahrheit.soll', {soll: bewertung.soll}) }}</template></span>
            </li>
        </ul>
        <ol class="m-0 flex list-none flex-col gap-0.5 p-0" :aria-label="t('wahrheit.pfad')">
            <li v-for="schritt in vergleich.schritte" :key="schritt.knoten" :class="['rounded px-1.5 py-0.5', SCHRITT[schritt.stand]]" :aria-current="schritt.stand === 'hier' ? 'step' : undefined">
                <span class="text-gedaempft">{{ schritt.frage }}</span> · <b>{{ schritt.soll || t('editor.leer') }}</b>
                <span v-if="schritt.stand === 'anders'"> · {{ t('wahrheit.trainee', {ist: schritt.ist}) }}</span>
                <span v-if="vergleich.abzweigung?.knoten === schritt.knoten" class="ml-1 text-xs font-bold uppercase">{{ t('wahrheit.abzweigung') }}</span>
            </li>
        </ol>
        <p v-if="vergleich.abzweigung && !vergleich.schritte.some(s => s.knoten === vergleich.abzweigung!.knoten)" class="m-0 rounded bg-red-50 p-2 text-fehler">{{ t('wahrheit.abzweigungAbseits', {frage: vergleich.abzweigung.frage, ist: vergleich.abzweigung.ist}) }}</p>
        <p v-if="vergleich.abseits" class="m-0 rounded bg-amber-100 p-2" role="status">
            {{ t('wahrheit.abseits', {frage: vergleich.abseits.frage}) }}
            <b>{{ vergleich.abseits.soll ?? t('wahrheit.improvisieren') }}</b>
        </p>
    </section>
</template>
