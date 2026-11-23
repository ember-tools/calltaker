<script setup lang="ts">
import {computed, nextTick, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import CodeAnzeige from '../components/CodeAnzeige.vue'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import LiveAnsicht from '../components/LiveAnsicht.vue'
import GeneratorPanel from '../components/GeneratorPanel.vue'
import PoolDatei from '../components/PoolDatei.vue'
import PoolListe from '../components/PoolListe.vue'
import SzenarioEditor from '../components/SzenarioEditor.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import VerbindungsZeichen from '../components/VerbindungsZeichen.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {useExportErinnerung} from '../composables/useExportErinnerung'
import {usePoolEditor} from '../composables/usePoolEditor'
import {useUebung} from '../composables/useUebung'

const props = defineProps<{code: string}>()

const {t} = useI18n()
const {zustand, erreichbar, unbekannt, absicht} = useUebung<'ausbilder'>(props.code)
const {graph, schwerste, fehler: graphFehler} = useAbfragegraph()
const pool = computed(() => zustand.value?.pool)
const poolBefunde = computed(() => zustand.value?.poolBefunde)
const poolStand = computed(() => zustand.value?.poolStand)
const editor = usePoolEditor(pool, poolBefunde, graph, absicht, {gezogen: t('editor.gezogen')})
const {entwurf, fehler, hinweis, listenFehler, befunde, ungespeichert} = editor
const {geaendert, exportiert} = useExportErinnerung(poolStand)
const REITER = ['live', 'pool'] as const
const reiter = ref<typeof REITER[number]>('live')

/**
 * Moves between the tabs with the arrow keys, as tab lists do.
 *
 * @param ereignis the key pressed on a tab
 */
function reiterTaste(ereignis: KeyboardEvent): void {
    if (ereignis.key !== 'ArrowLeft' && ereignis.key !== 'ArrowRight') return
    const schritt = ereignis.key === 'ArrowRight' ? 1 : -1
    reiter.value = REITER[(REITER.indexOf(reiter.value) + schritt + REITER.length) % REITER.length]!
    void nextTick(() => document.getElementById(`reiter-${reiter.value}`)?.focus())
}
</script>

<template>
    <div class="min-h-screen">
        <KopfLeiste :rolle="t('ausbilder.titel')">
            <template v-if="zustand">
                <CodeAnzeige :titel="t('codes.ausbilder')" :code="zustand.codes.ausbilder"/>
                <CodeAnzeige :titel="t('codes.trainee')" :code="zustand.codes.trainee"/>
                <VerbindungsZeichen :name="t('verbindung.trainee')" :verbunden="zustand.verbunden.trainee"/>
            </template>
        </KopfLeiste>
        <GetrenntHinweis v-if="!erreichbar"/>
        <UnbekannteUebung v-if="unbekannt"/>
        <p v-else-if="!zustand" class="m-0 p-5 text-gedaempft">{{ t('allgemein.laden') }}</p>
        <div v-else class="flex flex-col gap-3 p-5">
            <div role="tablist" class="flex gap-1 border-b border-rand">
                <button v-for="name in REITER" :id="`reiter-${name}`" :key="name" type="button" role="tab" :aria-selected="reiter === name" :aria-controls="`tafel-${name}`" :tabindex="reiter === name ? 0 : -1" :class="['-mb-px rounded-t border px-4 py-1.5 text-sm font-semibold', reiter === name ? 'border-rand border-b-white bg-white' : 'border-transparent text-gedaempft']" @click="reiter = name" @keydown="reiterTaste">{{ t(`reiter.${name}`) }}</button>
            </div>
            <div v-if="reiter === 'live'" id="tafel-live" role="tabpanel" aria-labelledby="reiter-live">
                <LiveAnsicht v-if="graph" :zustand="zustand" :graph="graph" :schwerste="schwerste" :absicht="absicht"/>
                <p v-else-if="graphFehler" role="alert" class="m-0 text-fehler">{{ t('ausbilder.graphFehlt', {fehler: graphFehler}) }}</p>
                <p v-else class="m-0 text-gedaempft">{{ t('allgemein.laden') }}</p>
            </div>
            <main v-else id="tafel-pool" role="tabpanel" aria-labelledby="reiter-pool" class="flex flex-wrap items-start gap-5">
                <section class="flex min-w-0 flex-[1_1_26rem] flex-col gap-3 rounded-lg border border-rand bg-flaeche p-4">
                    <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('ausbilder.pool') }}</h2>
                    <p v-if="zustand.pool.length === 0" class="m-0 text-sm text-gedaempft">{{ t('ausbilder.poolLeer') }}</p>
                    <PoolListe v-else :pool="zustand.pool" :befunde="zustand.poolBefunde" :gewaehlt="entwurf?.id" :gesperrt="ungespeichert" @bearbeiten="editor.bearbeiten" @entfernen="editor.entfernen" @verschieben="editor.verschieben"/>
                    <p v-if="listenFehler" class="m-0 text-sm text-fehler" role="alert">{{ listenFehler }}</p>
                    <p v-if="ungespeichert" class="m-0 text-xs text-gedaempft">{{ t('pool.erstSpeichern') }}</p>
                    <button type="button" :disabled="!graph || ungespeichert" class="self-start rounded bg-tinte px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40" @click="editor.neu">{{ t('pool.neu') }}</button>
                    <GeneratorPanel :erzeugung="zustand.erzeugung" :graph="graph ?? undefined" :auto-generieren="zustand.engine.parameter.autoGenerieren" :absicht="absicht"/>
                    <PoolDatei :code="code" :absicht="absicht" @exportiert="exportiert"/>
                    <p v-if="geaendert" class="m-0 text-xs text-warnung">{{ t('pool.nichtGesichert') }}</p>
                </section>
                <section v-if="entwurf && graph" class="flex min-w-0 flex-[2_1_36rem] flex-col gap-3 rounded-lg border border-rand bg-flaeche p-4">
                    <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ entwurf.id ? t('editor.bearbeiten') : t('editor.neu') }}</h2>
                    <SzenarioEditor v-model="entwurf" :graph="graph" :schwerste="schwerste" :befunde="befunde" :fehler="fehler" :hinweis="hinweis" @speichern="editor.speichern" @abbrechen="editor.schliessen"/>
                </section>
            </main>
        </div>
    </div>
</template>
