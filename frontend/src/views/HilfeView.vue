<script setup lang="ts">
import {breadcrumbData, HelpIndex, HelpPage, helpPath, HelpSection, HelpTopic, usePage} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import ToolHeader from '../components/ToolHeader.vue'
import {useHelpTexts, useHelpTopics} from '../composables/useHelpTopics'

/** The overview of the help center: what the Calltaker is, and one card per topic. */
const {t} = useI18n()
const texts = useHelpTexts()
const topics = useHelpTopics()

usePage({
    title: t('hilfe.seitentitel'),
    description: t('hilfe.description'),
    path: helpPath(),
    structuredData: [breadcrumbData([{name: t('app.name'), path: '/'}, {name: t('hilfe.breadcrumb'), path: helpPath()}])],
})
</script>

<template>
    <ToolHeader :role="t('hilfe.titel')"/>
    <HelpPage :title="t('hilfe.titel')">
        <HelpSection :title="t('hilfe.ueberblick.titel')">
            <HelpTopic :paragraphs="texts('ueberblick.text', 'ueberblick.rollen')"/>
        </HelpSection>
        <HelpIndex :topics="topics"/>
    </HelpPage>
</template>
