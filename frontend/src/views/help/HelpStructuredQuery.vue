<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import HinweisListe from '../../components/HinweisListe.vue'
import SnaFenster from '../../components/SnaFenster.vue'
import {useHelpExamples} from '../../composables/useHelpExamples'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: the structured emergency call query, its guiding questions and the advice to read out. */
const {t} = useI18n()
const texts = useHelpTexts()
const {graph, schwerste, call, entries} = useHelpExamples()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('trainee.sna')" :mockup="graph ? t('hilfe.trainee.snaMockup') : undefined">
            <template v-if="graph">
                <SnaFenster :model-value="{pfad: []}" :graph="graph" :schwerste="schwerste" :gesperrt="false" :seit="call.angenommenUm" uebergabe="gesperrt"/>
            </template>
        </HelpTopic>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.leitfragenTitel')">
        <HelpTopic :paragraphs="texts('trainee.leitfragen', 'trainee.leitfragenSicherheit')"/>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.hinweiseTitel')">
        <HelpTopic :paragraphs="texts('trainee.hinweise')" :mockup="graph && entries ? t('hilfe.trainee.hinweiseMockup') : undefined">
            <template v-if="graph && entries">
                <HinweisListe :model-value="entries" :graph="graph"/>
            </template>
        </HelpTopic>
    </HelpSection>
</template>
