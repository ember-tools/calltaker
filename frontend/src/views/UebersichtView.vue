<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import KopfLeiste from '../components/KopfLeiste.vue'
import Rueckweg from '../components/Rueckweg.vue'
import UebersichtTabelle from '../components/UebersichtTabelle.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {useAuswertung} from '../composables/useAuswertung'
import {useUebung} from '../composables/useUebung'
import type {Rolle, ZustandFuer} from '../modell/uebung'
import {gesamtVon, protokoll, zeileVon} from '../phasen/uebersicht'

const props = defineProps<{code: string, rolle: Rolle}>()

const {t} = useI18n()
const {zustand, unbekannt} = useUebung<Rolle>(props.code)
const {graph, fehler} = useAbfragegraph()
const {anrufe, ausgewertet} = useAuswertung(zustand, props.rolle)
const zeilen = computed(() => (graph.value ? ausgewertet.value.map(eintrag => zeileVon(graph.value!, eintrag)) : []))
const gesamt = computed(() => gesamtVon(anrufe.value, zeilen.value))
const sekunden = (wert?: number) => (wert === undefined ? t('debrief.nichtErreicht') : t('auswertung.sekunden', {sekunden: wert}))
const mittel = computed(() => sekunden(gesamt.value.mittelBisCode))
const mittelUebergabe = computed(() => sekunden(gesamt.value.mittelBisUebergabe))

function herunterladen(): void {
    if (!graph.value || !zustand.value) return
    const inhalt = protokoll(graph.value, (zustand.value as ZustandFuer<'ausbilder'>).anrufe, new Date(), zustand.value.engine.ziele)
    const adresse = URL.createObjectURL(new Blob([JSON.stringify(inhalt, null, 2)], {type: 'application/json'}))
    const link = document.createElement('a')
    link.href = adresse
    link.download = `calltaker-protokoll-${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(adresse)
}
</script>

<template>
    <div class="min-h-screen">
        <KopfLeiste :rolle="t('auswertung.uebersicht')">
            <Rueckweg :code="code" :rolle="rolle"/>
        </KopfLeiste>
        <UnbekannteUebung v-if="unbekannt"/>
        <main v-else class="mx-auto flex max-w-5xl flex-col gap-4 p-5">
            <p v-if="fehler" role="alert" class="m-0 text-fehler">{{ t('trainee.graphFehlt', {fehler}) }}</p>
            <p v-else-if="!zustand || !graph" class="m-0 text-gedaempft">{{ t('allgemein.laden') }}</p>
            <template v-else>
                <dl class="m-0 grid grid-cols-2 gap-3 sm:grid-cols-5" :aria-label="t('auswertung.gesamt')">
                    <div class="rounded border border-rand p-3"><dt class="text-xs text-gedaempft">{{ t('auswertung.anrufe') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.anrufe }}</dd></div>
                    <div class="rounded border border-rand p-3"><dt class="text-xs text-gedaempft">{{ t('auswertung.beendetAufgelegt') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.beendet }} / {{ gesamt.aufgelegt }}</dd></div>
                    <div class="rounded border border-rand p-3"><dt class="text-xs text-gedaempft">{{ t('auswertung.codes') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.codeExakt }} / {{ gesamt.codeNah }}</dd></div>
                    <div class="rounded border border-rand p-3"><dt class="text-xs text-gedaempft">{{ t('auswertung.bisCode') }}</dt><dd class="m-0 text-2xl font-bold">{{ mittel }}</dd></div>
                    <div class="rounded border border-rand p-3"><dt class="text-xs text-gedaempft">{{ t('auswertung.bisUebergabe') }}</dt><dd class="m-0 text-2xl font-bold">{{ mittelUebergabe }}</dd></div>
                </dl>
                <UebersichtTabelle :zeilen="zeilen" :code="code" :rolle="rolle"/>
                <button v-if="rolle === 'ausbilder'" type="button" class="self-start rounded bg-tinte px-4 py-1.5 text-sm font-semibold text-white" @click="herunterladen">{{ t('auswertung.export') }}</button>
            </template>
        </main>
    </div>
</template>
