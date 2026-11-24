<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import CodeAnzeige from '../components/CodeAnzeige.vue'
import EinsatzMaske from '../components/EinsatzMaske.vue'
import HilfeAbschnitt from '../components/HilfeAbschnitt.vue'
import HilfeThema from '../components/HilfeThema.vue'
import HinweisListe from '../components/HinweisListe.vue'
import ReanimationsLeiste from '../components/ReanimationsLeiste.vue'
import SchrittLeiste from '../components/SchrittLeiste.vue'
import SnaFenster from '../components/SnaFenster.vue'
import WahrheitsKarte from '../components/WahrheitsKarte.vue'
import WarntafelFeld from '../components/WarntafelFeld.vue'
import WarteschlangeLeiste from '../components/WarteschlangeLeiste.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {beispielAnruf, beispielEintraege, beispielReanimation, beispielSchlange, beispielWahrheit} from '../modell/hilfebeispiele'
import {phasenstand} from '../phasen/register'

const {t} = useI18n()
const {graph, schwerste} = useAbfragegraph()
const jetzt = Date.now() / 1000

const schlange = beispielSchlange(jetzt)
const anruf = beispielAnruf(jetzt)
const eintraege = computed(() => (graph.value ? beispielEintraege(graph.value) : undefined))
const reanimation = ref(beispielReanimation(jetzt))
const tafel = ref({un: '1203', gefahrenzahl: '33'})
const wahrheit = computed(() => (graph.value ? beispielWahrheit(graph.value, jetzt) : undefined))
const staende = computed(() => (graph.value && eintraege.value ? phasenstand(eintraege.value, {graph: graph.value, anruf}) : []))
const aktivePhase = computed(() => staende.value.find(stand => stand.fehlend.length > 0)?.phase.id ?? '')
const TASTEN = ['F2', 'F3', 'F4', 'F9', 'Alt+Ziffer'] as const

/**
 * The texts of a topic, by their catalogue keys under `hilfe`.
 *
 * @param schluessel the keys
 * @returns the texts
 */
function texte(...schluessel: string[]): string[] {
    return schluessel.map(s => t(`hilfe.${s}`))
}

let vorher = ''

onMounted(() => {
    vorher = document.title
    document.title = t('hilfe.seitentitel')
})

onBeforeUnmount(() => {
    document.title = vorher
})
</script>

<template>
    <main class="mx-auto flex w-full max-w-4xl flex-col gap-6 p-5">
        <header class="flex flex-col gap-1 text-center">
            <h1 class="m-0 font-condensed text-3xl font-bold tracking-wide">{{ t('hilfe.titel') }}</h1>
            <RouterLink :to="{name: 'start'}" class="text-sm text-akzent underline">{{ t('hilfe.zurueck') }}</RouterLink>
        </header>
        <HilfeAbschnitt :titel="t('hilfe.ueberblick.titel')">
            <HilfeThema :texte="texte('ueberblick.text', 'ueberblick.rollen')"/>
        </HilfeAbschnitt>
        <HilfeAbschnitt :titel="t('hilfe.start.titel')">
            <HilfeThema :texte="texte('start.anlegen', 'start.codes', 'start.beitreten')" :mockup="t('hilfe.start.mockup')">
                <div class="flex flex-wrap gap-3 rounded bg-leiste p-3 text-white">
                    <CodeAnzeige :titel="t('codes.ausbilder')" code="A-7K2M9QX4"/>
                    <CodeAnzeige :titel="t('codes.trainee')" code="T-3PL8WD2N"/>
                </div>
            </HilfeThema>
        </HilfeAbschnitt>
        <HilfeAbschnitt :titel="t('hilfe.trainee.titel')">
            <HilfeThema :titel="t('hilfe.trainee.schlangeTitel')" :texte="texte('trainee.schlange')" :mockup="t('hilfe.trainee.schlangeMockup')">
                <div class="rounded bg-leiste p-3 text-white"><WarteschlangeLeiste :zustand="schlange"/></div>
            </HilfeThema>
            <HilfeThema v-if="eintraege" :titel="t('hilfe.trainee.maskeTitel')" :texte="texte('trainee.maske', 'trainee.funkzelle')" :mockup="t('hilfe.trainee.maskeMockup')">
                <SchrittLeiste :staende="staende" :aktiv="aktivePhase" class="mb-3"/>
                <EinsatzMaske :model-value="eintraege" :anruf="anruf" ruhig class="max-w-lg"/>
            </HilfeThema>
            <HilfeThema v-if="graph" :titel="t('hilfe.trainee.snaTitel')" :texte="texte('trainee.sna')" :mockup="t('hilfe.trainee.snaMockup')">
                <SnaFenster :model-value="{pfad: []}" :graph="graph" :schwerste="schwerste" :gesperrt="false" :seit="anruf.angenommenUm" uebergabe="gesperrt"/>
            </HilfeThema>
            <HilfeThema :titel="t('hilfe.trainee.leitfragenTitel')" :texte="texte('trainee.leitfragen', 'trainee.leitfragenSicherheit')"/>
            <HilfeThema v-if="graph && eintraege" :titel="t('hilfe.trainee.hinweiseTitel')" :texte="texte('trainee.hinweise')" :mockup="t('hilfe.trainee.hinweiseMockup')">
                <HinweisListe :model-value="eintraege" :graph="graph"/>
            </HilfeThema>
            <HilfeThema v-if="graph" :titel="t('hilfe.trainee.reanimationTitel')" :texte="texte('trainee.reanimation', 'trainee.reanimationGruppen')" :mockup="t('hilfe.trainee.reanimationMockup')">
                <ReanimationsLeiste v-model="reanimation" :graph="graph" :eintreffen-um="jetzt + 3600" ruhig/>
            </HilfeThema>
            <HilfeThema :titel="t('hilfe.trainee.tafelTitel')" :texte="texte('trainee.tafel')" :mockup="t('hilfe.trainee.tafelMockup')">
                <WarntafelFeld v-model="tafel"/>
            </HilfeThema>
            <HilfeThema :titel="t('hilfe.trainee.uebergabeTitel')" :texte="texte('trainee.uebergabe', 'trainee.beenden')"/>
            <HilfeThema :titel="t('hilfe.trainee.tastenTitel')" :texte="[]">
                <template #inhalt>
                    <dl class="m-0 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
                        <template v-for="taste in TASTEN" :key="taste">
                            <dt><kbd class="rounded border border-slate-400 bg-white px-1.5 font-mono">{{ taste }}</kbd></dt>
                            <dd class="m-0 text-gedaempft">{{ t(`hilfe.trainee.taste.${taste}`) }}</dd>
                        </template>
                    </dl>
                </template>
            </HilfeThema>
        </HilfeAbschnitt>
        <HilfeAbschnitt :titel="t('hilfe.ausbilder.titel')">
            <HilfeThema v-if="graph && wahrheit" :titel="t('hilfe.ausbilder.liveTitel')" :texte="texte('ausbilder.live', 'ausbilder.wahrheit', 'ausbilder.leitfragen')" :mockup="t('hilfe.ausbilder.wahrheitMockup')">
                <WahrheitsKarte :graph="graph" :anruf="wahrheit" class="max-w-md"/>
            </HilfeThema>
            <HilfeThema :titel="t('hilfe.ausbilder.anruferTitel')" :texte="texte('ausbilder.hand', 'ausbilder.beziehung', 'ausbilder.beschwerden', 'ausbilder.beobachtet')"/>
            <HilfeThema :titel="t('hilfe.ausbilder.schlangeTitel')" :texte="texte('ausbilder.schlange')"/>
            <HilfeThema :titel="t('hilfe.ausbilder.poolTitel')" :texte="texte('ausbilder.pool', 'ausbilder.generator', 'ausbilder.belastende')"/>
        </HilfeAbschnitt>
        <HilfeAbschnitt :titel="t('hilfe.auswertung.titel')">
            <HilfeThema :texte="texte('auswertung.debrief', 'auswertung.leitfragen', 'auswertung.uebersicht')"/>
        </HilfeAbschnitt>
        <HilfeAbschnitt :titel="t('hilfe.tipps.titel')">
            <HilfeThema :texte="texte('tipps.zwei', 'tipps.ton', 'tipps.version', 'tipps.daten')"/>
        </HilfeAbschnitt>
    </main>
</template>
