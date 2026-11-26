<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: how the trainer plays the caller. */
const texts = useHelpTexts()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('ausbilder.hand', 'ausbilder.beziehung', 'ausbilder.beschwerden', 'ausbilder.beobachtet')"/>
    </HelpSection>
</template>
