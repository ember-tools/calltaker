<script setup lang="ts">
import {CodeDisplay, HelpSection, HelpTopic} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: creating an exercise and joining it. */
const {t} = useI18n()
const texts = useHelpTexts()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('start.anlegen', 'start.codes', 'start.beitreten')" :mockup="t('hilfe.start.mockup')">
            <div class="flex flex-wrap gap-3">
                <CodeDisplay :title="t('codes.ausbilder')" code="A-7K2M9QX4"/>
                <CodeDisplay :title="t('codes.trainee')" code="T-3PL8WD2N"/>
            </div>
        </HelpTopic>
    </HelpSection>
</template>
