<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: the debrief after each call and the overview of the exercise. */
const texts = useHelpTexts()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('auswertung.debrief', 'auswertung.leitfragen', 'auswertung.uebersicht')"/>
    </HelpSection>
</template>
