<script setup lang="ts">
import {CodeDisplay, HelpPage, HelpSection, HelpTopic, usePage} from '@emberbox/ui'
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import ToolHeader from '../components/ToolHeader.vue'
import EinsatzMaske from '../components/EinsatzMaske.vue'
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

usePage({
    title: t('hilfe.seitentitel'),
    description: t('hilfe.description'),
    path: '/hilfe',
})
</script>

<template>
    <ToolHeader :role="t('hilfe.titel')"/>
    <HelpPage :title="t('hilfe.titel')">
        <HelpSection :title="t('hilfe.ueberblick.titel')">
            <HelpTopic :paragraphs="texte('ueberblick.text', 'ueberblick.rollen')"/>
        </HelpSection>
        <HelpSection :title="t('hilfe.start.titel')">
            <HelpTopic :paragraphs="texte('start.anlegen', 'start.codes', 'start.beitreten')" :mockup="t('hilfe.start.mockup')">
                <div class="flex flex-wrap gap-3">
                    <CodeDisplay :title="t('codes.ausbilder')" code="A-7K2M9QX4"/>
                    <CodeDisplay :title="t('codes.trainee')" code="T-3PL8WD2N"/>
                </div>
            </HelpTopic>
        </HelpSection>
        <HelpSection :title="t('hilfe.trainee.titel')">
            <HelpTopic :title="t('hilfe.trainee.schlangeTitel')" :paragraphs="texte('trainee.schlange')" :mockup="t('hilfe.trainee.schlangeMockup')">
                <div class="rounded-sm bg-default p-3"><WarteschlangeLeiste :zustand="schlange" quiet/></div>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.maskeTitel')" :paragraphs="texte('trainee.maske', 'trainee.funkzelle')" :mockup="eintraege ? t('hilfe.trainee.maskeMockup') : undefined">
                <template v-if="eintraege">
                    <SchrittLeiste :staende="staende" :aktiv="aktivePhase" class="mb-3"/>
                    <EinsatzMaske :model-value="eintraege" :anruf="anruf" ruhig class="max-w-lg"/>
                </template>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.snaTitel')" :paragraphs="texte('trainee.sna')" :mockup="graph ? t('hilfe.trainee.snaMockup') : undefined">
                <template v-if="graph">
                    <SnaFenster :model-value="{pfad: []}" :graph="graph" :schwerste="schwerste" :gesperrt="false" :seit="anruf.angenommenUm" uebergabe="gesperrt"/>
                </template>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.leitfragenTitel')" :paragraphs="texte('trainee.leitfragen', 'trainee.leitfragenSicherheit')"/>
            <HelpTopic :title="t('hilfe.trainee.hinweiseTitel')" :paragraphs="texte('trainee.hinweise')" :mockup="graph && eintraege ? t('hilfe.trainee.hinweiseMockup') : undefined">
                <template v-if="graph && eintraege">
                    <HinweisListe :model-value="eintraege" :graph="graph"/>
                </template>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.reanimationTitel')" :paragraphs="texte('trainee.reanimation', 'trainee.reanimationGruppen')" :mockup="graph ? t('hilfe.trainee.reanimationMockup') : undefined">
                <template v-if="graph">
                    <ReanimationsLeiste v-model="reanimation" :graph="graph" :eintreffen-um="jetzt + 3600" ruhig/>
                </template>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.tafelTitel')" :paragraphs="texte('trainee.tafel')" :mockup="t('hilfe.trainee.tafelMockup')">
                <WarntafelFeld v-model="tafel"/>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.trainee.uebergabeTitel')" :paragraphs="texte('trainee.uebergabe', 'trainee.beenden')"/>
            <HelpTopic :title="t('hilfe.trainee.tastenTitel')" :paragraphs="[]">
                <template #content>
                    <dl class="m-0 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
                        <template v-for="taste in TASTEN" :key="taste">
                            <dt><kbd class="rounded border border-accented bg-default px-1.5 font-mono">{{ taste }}</kbd></dt>
                            <dd class="m-0 text-muted">{{ t(`hilfe.trainee.taste.${taste}`) }}</dd>
                        </template>
                    </dl>
                </template>
            </HelpTopic>
        </HelpSection>
        <HelpSection :title="t('hilfe.ausbilder.titel')">
            <HelpTopic :title="t('hilfe.ausbilder.liveTitel')" :paragraphs="texte('ausbilder.live', 'ausbilder.wahrheit', 'ausbilder.leitfragen')" :mockup="graph && wahrheit ? t('hilfe.ausbilder.wahrheitMockup') : undefined">
                <template v-if="graph && wahrheit">
                    <WahrheitsKarte :graph="graph" :anruf="wahrheit" class="max-w-md"/>
                </template>
            </HelpTopic>
            <HelpTopic :title="t('hilfe.ausbilder.anruferTitel')" :paragraphs="texte('ausbilder.hand', 'ausbilder.beziehung', 'ausbilder.beschwerden', 'ausbilder.beobachtet')"/>
            <HelpTopic :title="t('hilfe.ausbilder.schlangeTitel')" :paragraphs="texte('ausbilder.schlange')"/>
            <HelpTopic :title="t('hilfe.ausbilder.poolTitel')" :paragraphs="texte('ausbilder.pool', 'ausbilder.generator', 'ausbilder.belastende')"/>
        </HelpSection>
        <HelpSection :title="t('hilfe.auswertung.titel')">
            <HelpTopic :paragraphs="texte('auswertung.debrief', 'auswertung.leitfragen', 'auswertung.uebersicht')"/>
        </HelpSection>
        <HelpSection :title="t('hilfe.tipps.titel')">
            <HelpTopic :paragraphs="texte('tipps.zwei', 'tipps.ton', 'tipps.version', 'tipps.daten')"/>
        </HelpSection>
    </HelpPage>
</template>
