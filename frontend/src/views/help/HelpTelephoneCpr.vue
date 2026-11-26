<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import ReanimationsLeiste from '../../components/ReanimationsLeiste.vue'
import {useHelpExamples} from '../../composables/useHelpExamples'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: guiding a caller through resuscitation. */
const {t} = useI18n()
const texts = useHelpTexts()
const {graph, now, resuscitation} = useHelpExamples()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('trainee.reanimation', 'trainee.reanimationGruppen', 'tipps.ton')" :mockup="graph ? t('hilfe.trainee.reanimationMockup') : undefined">
            <template v-if="graph">
                <ReanimationsLeiste v-model="resuscitation" :graph="graph" :eintreffen-um="now + 3600" ruhig/>
            </template>
        </HelpTopic>
    </HelpSection>
</template>
