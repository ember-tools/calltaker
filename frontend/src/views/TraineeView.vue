<script setup lang="ts">
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import GespraechAbschluss from '../components/GespraechAbschluss.vue'
import GespraechsFlaeche from '../components/GespraechsFlaeche.vue'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import VerbindungsZeichen from '../components/VerbindungsZeichen.vue'
import WarteschlangeLeiste from '../components/WarteschlangeLeiste.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {useGespraech} from '../composables/useGespraech'
import {useSpiegel} from '../composables/useSpiegel'
import {useUebung} from '../composables/useUebung'
import {endergebnis} from '../modell/abfrageweg'
import {leererFensterzustand, type Fensterzustand} from '../modell/fensterzustand'
import {nochOffen} from '../phasen/register'

const props = defineProps<{code: string}>()

const {t} = useI18n()
const {zustand, erreichbar, unbekannt, absicht} = useUebung<'trainee'>(props.code)
const {graph, schwerste, fehler} = useAbfragegraph()
const anruf = computed(() => zustand.value?.anrufe.find(a => a.zustand === 'gespraech'))
const {eintraege, jetztSenden} = useGespraech(anruf, absicht)
const suche = ref('')
const fenster = ref<Fensterzustand>(leererFensterzustand())
useSpiegel(computed(() => ({suche: suche.value, ...fenster.value})), absicht)

const kontext = computed(() => (graph.value && anruf.value ? {graph: graph.value, anruf: anruf.value} : undefined))
const offen = computed(() => (kontext.value ? nochOffen(eintraege.value, kontext.value) : []))
const ergebnis = computed(() => (graph.value ? endergebnis(graph.value, eintraege.value.abfrage) : undefined))
const zuletzt = computed(() => zustand.value?.anrufe.filter(a => a.zustand === 'beendet').at(-1))
const flaeche = ref<InstanceType<typeof GespraechsFlaeche> | null>(null)

watch(() => anruf.value?.id, () => {
    suche.value = ''
    fenster.value = leererFensterzustand()
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
    flaeche.value?.snaZeigen()
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
            <GespraechsFlaeche ref="flaeche" v-model="eintraege" v-model:suche="suche" v-model:ui="fenster" :graph="graph" :schwerste="schwerste" :anruf="anruf" @sofort="jetztSenden"/>
            <GespraechAbschluss :offen="offen" @beenden="beenden"/>
        </main>
        <main v-else class="p-5">
            <p class="m-0 text-gedaempft">{{ !zustand ? t('allgemein.laden') : zuletzt ? t('trainee.beendet') : t('trainee.warten') }}</p>
        </main>
    </div>
</template>
