<script setup lang="ts">
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import EinsatzMaske from '../components/EinsatzMaske.vue'
import GespraechAbschluss from '../components/GespraechAbschluss.vue'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import SchrittLeiste from '../components/SchrittLeiste.vue'
import SnaFenster from '../components/SnaFenster.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import VerbindungsZeichen from '../components/VerbindungsZeichen.vue'
import WarteschlangeLeiste from '../components/WarteschlangeLeiste.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {useGespraech} from '../composables/useGespraech'
import {useSpiegel} from '../composables/useSpiegel'
import {useUebung} from '../composables/useUebung'
import {endergebnis} from '../modell/abfrageweg'
import {nochOffen, phasenstand} from '../phasen/register'

const props = defineProps<{code: string}>()

const {t} = useI18n()
const {zustand, erreichbar, unbekannt, absicht} = useUebung<'trainee'>(props.code)
const {graph, schwerste, fehler} = useAbfragegraph()
const anruf = computed(() => zustand.value?.anrufe.find(a => a.zustand === 'gespraech'))
const {eintraege, jetztSenden} = useGespraech(anruf, absicht)
const suche = ref('')
useSpiegel(computed(() => ({suche: suche.value})), absicht)

const kontext = computed(() => (graph.value && anruf.value ? {graph: graph.value, anruf: anruf.value} : undefined))
const staende = computed(() => (kontext.value ? phasenstand(eintraege.value, kontext.value) : []))
const aktivePhase = computed(() => staende.value.find(stand => stand.fehlend.length > 0)?.phase.id ?? '')
const offen = computed(() => (kontext.value ? nochOffen(eintraege.value, kontext.value) : []))
const ergebnis = computed(() => (graph.value ? endergebnis(graph.value, eintraege.value.abfrage) : undefined))
const alter = computed(() => eintraege.value.abfrage.pfad.find(schritt => schritt.knoten === 'rd.alter')?.wert)
const zuletzt = computed(() => zustand.value?.anrufe.filter(a => a.zustand === 'beendet').at(-1))
const sna = ref<InstanceType<typeof SnaFenster> | null>(null)

watch(() => anruf.value?.id, () => {
    suche.value = ''
})

watch(ergebnis, wert => {
    eintraege.value.abfrage.codeErreicht = Boolean(wert)
}, {flush: 'sync'})

watch(() => Boolean(eintraege.value.ort.koordinaten), (gesetzt, vorher) => {
    if (gesetzt && !vorher) void nextTick(snaZeigen)
})

async function beenden(): Promise<void> {
    await jetztSenden()
    await absicht('beenden')
}

function snaZeigen(): void {
    sna.value?.fokussieren()
}
</script>

<template>
    <div class="flex min-h-screen flex-col">
        <KopfLeiste :rolle="t('trainee.titel')">
            <WarteschlangeLeiste v-if="zustand" class="flex-1" :zustand="zustand" @bereit="absicht('bereit')" @annehmen="id => absicht('annehmen', {anrufId: id})"/>
            <VerbindungsZeichen v-if="zustand" :name="t('verbindung.ausbilder')" :verbunden="zustand.verbunden.ausbilder"/>
        </KopfLeiste>
        <GetrenntHinweis v-if="!erreichbar"/>
        <UnbekannteUebung v-if="unbekannt"/>
        <p v-else-if="fehler" role="alert" class="m-0 p-5 text-fehler">{{ t('trainee.graphFehlt', {fehler}) }}</p>
        <main v-else-if="anruf && graph" class="flex flex-1 flex-col gap-3 p-4">
            <SchrittLeiste :staende="staende" :aktiv="aktivePhase"/>
            <div class="flex flex-wrap gap-4">
                <EinsatzMaske v-model="eintraege" v-model:suche="suche" class="max-w-lg min-w-0 flex-[1_1_26rem]" :anruf="anruf" :stichwort="ergebnis ? `${ergebnis.code} · ${ergebnis.kategorie}` : ''" :alter="alter" @sna="snaZeigen" @sofort="jetztSenden"/>
                <div class="min-w-0 flex-[999_1_36rem]">
                    <SnaFenster ref="sna" v-model="eintraege.abfrage" :graph="graph" :schwerste="schwerste" :gesperrt="!eintraege.ort.koordinaten" :seit="anruf.angenommenUm" @sofort="jetztSenden"/>
                </div>
            </div>
            <GespraechAbschluss :offen="offen" @beenden="beenden"/>
        </main>
        <main v-else class="p-5">
            <p class="m-0 text-gedaempft">{{ !zustand ? t('allgemein.laden') : zuletzt ? t('trainee.beendet') : t('trainee.warten') }}</p>
        </main>
    </div>
</template>
