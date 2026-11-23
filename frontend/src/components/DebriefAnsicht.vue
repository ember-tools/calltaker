<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {dauer} from '../composables/useUhr'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Szenario} from '../modell/szenario'
import type {AnrufSicht} from '../modell/uebung'
import {debrief} from '../phasen/debrief'
import type {Bewertung, Urteil} from '../phasen/typen'
import PfadVergleichListe from './PfadVergleichListe.vue'

const props = defineProps<{graph: Abfragegraph, anruf: AnrufSicht, szenario: Szenario}>()

const {t} = useI18n()
const ergebnis = computed(() => debrief(props.graph, props.anruf, props.szenario))
const ziel = computed(() => props.graph.knoten[props.szenario.ziel.knoten])
const ZEITEN = ['annahme', 'adresse', 'code', 'gespraech'] as const
const URTEIL: Record<Urteil, string> = {richtig: 'bg-green-50 text-ok', teilweise: 'bg-amber-50 text-warnung', falsch: 'bg-red-50 text-fehler', offen: 'bg-red-50 text-fehler', hinweis: ''}

/**
 * What the trainee entered, as the table shows it.
 *
 * @param bewertung the comparison
 * @returns the entry, the distance of a point, or that nothing was entered
 */
function erfasst(bewertung: Bewertung): string {
    if (bewertung.abstand !== undefined) return t('wahrheit.abstand', {meter: bewertung.abstand})
    if (bewertung.urteil === 'hinweis') return bewertung.ist
    return bewertung.ist || t('debrief.nichtErfasst')
}

/**
 * The verdict, with the tier of a code.
 *
 * @param bewertung the comparison
 * @returns the verdict as text
 */
function urteil(bewertung: Bewertung): string {
    const text = t(`debrief.urteil.${bewertung.urteil}`)
    return bewertung.stufe && bewertung.stufe !== 'exakt' ? `${text} (${t(`stufe.${bewertung.stufe}`)})` : text
}
</script>

<template>
    <article class="flex flex-col gap-4">
        <header class="flex flex-col gap-1">
            <h1 class="m-0 text-xl font-bold">{{ szenario.titel }}</h1>
            <p class="m-0"><b class="font-mono">{{ szenario.ziel.code }}</b> · {{ ziel?.kategorie }} · {{ ziel?.anlass }}</p>
        </header>
        <section v-for="phase in ergebnis.phasen" :key="phase.phase.id" :aria-label="t(phase.phase.titel)" class="flex flex-col gap-1">
            <h2 class="m-0 text-base font-bold">{{ t(phase.phase.titel) }}</h2>
            <table class="w-full border-collapse text-sm">
                <thead>
                    <tr class="text-left text-xs text-gedaempft"><th class="py-1 pr-2">{{ t('debrief.feld') }}</th><th class="py-1 pr-2">{{ t('debrief.erfasst') }}</th><th class="py-1 pr-2">{{ t('debrief.wahrheit') }}</th><th class="py-1">{{ t('debrief.ergebnis') }}</th></tr>
                </thead>
                <tbody>
                    <tr v-for="bewertung in phase.bewertungen" :key="bewertung.feld" :class="URTEIL[bewertung.urteil]">
                        <th scope="row" class="py-1 pr-2 text-left font-semibold">{{ t(bewertung.feld) }}</th>
                        <td class="py-1 pr-2">{{ erfasst(bewertung) }}</td>
                        <td class="py-1 pr-2">{{ bewertung.abstand !== undefined ? t('debrief.punktSoll') : bewertung.soll }}</td>
                        <td class="py-1 font-semibold">{{ urteil(bewertung) }}</td>
                    </tr>
                </tbody>
            </table>
        </section>
        <section :aria-label="t('debrief.zeiten')" class="flex flex-col gap-1">
            <h2 class="m-0 text-base font-bold">{{ t('debrief.zeiten') }}</h2>
            <dl class="m-0 grid grid-cols-[max-content_1fr] gap-x-3 text-sm">
                <template v-for="zeit in ZEITEN" :key="zeit">
                    <dt class="text-gedaempft">{{ t(`debrief.zeit.${zeit}`) }}</dt>
                    <dd class="m-0 font-mono">{{ ergebnis.zeiten[zeit] === undefined ? t('debrief.nichtErreicht') : dauer(ergebnis.zeiten[zeit]!) }}</dd>
                </template>
            </dl>
        </section>
        <section v-if="ergebnis.fehlend.length" :aria-label="t('debrief.fehlte')" class="rounded bg-red-50 p-3 text-sm text-fehler" role="status">
            <b>{{ t('debrief.fehlte') }}</b> {{ ergebnis.fehlend.map(schluessel => t(schluessel)).join(', ') }}
        </section>
        <section :aria-label="t('debrief.pfad')" class="flex flex-col gap-1 text-sm">
            <h2 class="m-0 text-base font-bold">{{ t('debrief.pfad') }}</h2>
            <p v-if="!ergebnis.pfad.abzweigung" class="m-0 text-ok">{{ t('debrief.ohneAbzweigung') }}</p>
            <PfadVergleichListe :vergleich="ergebnis.pfad"/>
        </section>
    </article>
</template>
