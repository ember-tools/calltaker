<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import WahrheitsKarte from '../../components/WahrheitsKarte.vue'
import {useHelpExamples} from '../../composables/useHelpExamples'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: what the trainer sees and steers. */
const {t} = useI18n()
const texts = useHelpTexts()
const {graph, truth} = useHelpExamples()
</script>

<template>
    <HelpSection :title="t('hilfe.ausbilder.liveTitel')">
        <HelpTopic :paragraphs="texts('ausbilder.live', 'ausbilder.wahrheit', 'ausbilder.leitfragen')" :mockup="graph && truth ? t('hilfe.ausbilder.wahrheitMockup') : undefined">
            <template v-if="graph && truth">
                <WahrheitsKarte :graph="graph" :anruf="truth" class="max-w-md"/>
            </template>
        </HelpTopic>
    </HelpSection>
    <HelpSection :title="t('hilfe.ausbilder.schlangeTitel')">
        <HelpTopic :paragraphs="texts('ausbilder.schlange')"/>
    </HelpSection>
    <HelpSection :title="t('hilfe.ausbilder.poolTitel')">
        <HelpTopic :paragraphs="texts('ausbilder.pool', 'ausbilder.generator', 'ausbilder.belastende')"/>
    </HelpSection>
</template>
