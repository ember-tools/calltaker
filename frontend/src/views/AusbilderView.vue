<script setup lang="ts">
import {CodeDisplay} from '@emberbox/ui'
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import ToolHeader from '../components/ToolHeader.vue'
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
const TABS = computed(() => [
    {label: t('reiter.live'), value: 'live', slot: 'live' as const},
    {label: t('reiter.pool'), value: 'pool', slot: 'pool' as const},
])
const tab = ref('live')
const traineeLink = computed(() => (zustand.value ? `${window.location.origin}/t/${zustand.value.codes.trainee}` : undefined))
</script>

<template>
    <div class="min-h-screen">
        <ToolHeader :role="t('ausbilder.titel')">
            <VerbindungsZeichen v-if="zustand" :name="t('verbindung.trainee')" :verbunden="zustand.verbunden.trainee"/>
        </ToolHeader>
        <GetrenntHinweis v-if="!erreichbar"/>
        <UnbekannteUebung v-if="unbekannt"/>
        <p v-else-if="!zustand" class="m-0 p-5 text-muted">{{ t('allgemein.laden') }}</p>
        <main v-else class="flex flex-col gap-3 p-5">
            <div class="flex flex-wrap gap-4">
                <CodeDisplay :title="t('codes.ausbilder')" :code="zustand.codes.ausbilder" hidden/>
                <CodeDisplay :title="t('codes.trainee')" :code="zustand.codes.trainee" :link="traineeLink" qr/>
            </div>
            <UTabs v-model="tab" :items="TABS" variant="link" :ui="{content: 'pt-3'}">
            <template #live>
                <LiveAnsicht v-if="graph" :zustand="zustand" :graph="graph" :schwerste="schwerste" :absicht="absicht"/>
                <p v-else-if="graphFehler" role="alert" class="m-0 text-error">{{ t('ausbilder.graphFehlt', {fehler: graphFehler}) }}</p>
                <p v-else class="m-0 text-muted">{{ t('allgemein.laden') }}</p>
            </template>
            <template #pool>
            <div class="flex flex-wrap items-start gap-5">
                <section class="flex min-w-0 flex-[1_1_26rem] flex-col gap-3 rounded-lg border border-default bg-default p-4">
                    <h2 class="section-title m-0">{{ t('ausbilder.pool') }}</h2>
                    <p v-if="zustand.pool.length === 0" class="m-0 text-sm text-muted">{{ t('ausbilder.poolLeer') }}</p>
                    <PoolListe v-else :pool="zustand.pool" :befunde="zustand.poolBefunde" :gewaehlt="entwurf?.id" :gesperrt="ungespeichert" @bearbeiten="editor.bearbeiten" @entfernen="editor.entfernen" @verschieben="editor.verschieben"/>
                    <p v-if="listenFehler" class="m-0 text-sm text-error" role="alert">{{ listenFehler }}</p>
                    <p v-if="ungespeichert" class="m-0 text-xs text-muted">{{ t('pool.erstSpeichern') }}</p>
                    <UButton size="sm" class="self-start" :disabled="!graph || ungespeichert" @click="editor.neu">{{ t('pool.neu') }}</UButton>
                    <GeneratorPanel :erzeugung="zustand.erzeugung" :graph="graph ?? undefined" :auto-generieren="zustand.engine.parameter.autoGenerieren" :absicht="absicht"/>
                    <PoolDatei :code="code" :absicht="absicht" @exportiert="exportiert"/>
                    <p v-if="geaendert" class="m-0 text-xs text-warning">{{ t('pool.nichtGesichert') }}</p>
                </section>
                <section v-if="entwurf && graph" class="flex min-w-0 flex-[2_1_36rem] flex-col gap-3 rounded-lg border border-default bg-default p-4">
                    <h2 class="section-title m-0">{{ entwurf.id ? t('editor.bearbeiten') : t('editor.neu') }}</h2>
                    <SzenarioEditor v-model="entwurf" :graph="graph" :schwerste="schwerste" :befunde="befunde" :fehler="fehler" :hinweis="hinweis" @speichern="editor.speichern" @abbrechen="editor.schliessen"/>
                </section>
            </div>
            </template>
            </UTabs>
        </main>
    </div>
</template>
