<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import ToolHeader from '../components/ToolHeader.vue'
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
        <ToolHeader :role="t('auswertung.uebersicht')">
            <Rueckweg :code="code" :rolle="rolle"/>
        </ToolHeader>
        <UnbekannteUebung v-if="unbekannt"/>
        <main v-else class="mx-auto flex max-w-5xl flex-col gap-4 p-5">
            <p v-if="fehler" role="alert" class="m-0 text-error">{{ t('trainee.graphFehlt', {fehler}) }}</p>
            <p v-else-if="!zustand || !graph" class="m-0 text-muted">{{ t('allgemein.laden') }}</p>
            <template v-else>
                <dl class="m-0 grid grid-cols-2 gap-3 sm:grid-cols-5" :aria-label="t('auswertung.gesamt')">
                    <div class="rounded border border-default p-3"><dt class="text-xs text-muted">{{ t('auswertung.anrufe') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.anrufe }}</dd></div>
                    <div class="rounded border border-default p-3"><dt class="text-xs text-muted">{{ t('auswertung.beendetAufgelegt') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.beendet }} / {{ gesamt.aufgelegt }}</dd></div>
                    <div class="rounded border border-default p-3"><dt class="text-xs text-muted">{{ t('auswertung.codes') }}</dt><dd class="m-0 text-2xl font-bold">{{ gesamt.codeExakt }} / {{ gesamt.codeNah }}</dd></div>
                    <div class="rounded border border-default p-3"><dt class="text-xs text-muted">{{ t('auswertung.bisCode') }}</dt><dd class="m-0 text-2xl font-bold">{{ mittel }}</dd></div>
                    <div class="rounded border border-default p-3"><dt class="text-xs text-muted">{{ t('auswertung.bisUebergabe') }}</dt><dd class="m-0 text-2xl font-bold">{{ mittelUebergabe }}</dd></div>
                </dl>
                <UebersichtTabelle :zeilen="zeilen" :code="code" :rolle="rolle"/>
                <UButton v-if="rolle === 'ausbilder'" size="sm" class="self-start" @click="herunterladen">{{ t('auswertung.export') }}</UButton>
            </template>
        </main>
    </div>
</template>
