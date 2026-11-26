<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: practical tips for running an exercise. */
const texts = useHelpTexts()
</script>

<template>
    <HelpSection>
        <HelpTopic :paragraphs="texts('tipps.zwei', 'tipps.ton', 'tipps.version', 'tipps.daten')"/>
    </HelpSection>
</template>
