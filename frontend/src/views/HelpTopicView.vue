<script setup lang="ts">
import {breadcrumbData, HelpPage, helpPath, usePage} from '@emberbox/ui'
import {type Component, computed} from 'vue'
import {useI18n} from 'vue-i18n'
import ToolHeader from '../components/ToolHeader.vue'
import {useHelpTopics} from '../composables/useHelpTopics'
import type {HelpSlug} from '../helpTopics'
import HelpDebrief from './help/HelpDebrief.vue'
import HelpFirstSteps from './help/HelpFirstSteps.vue'
import HelpPlayingTheCaller from './help/HelpPlayingTheCaller.vue'
import HelpStructuredQuery from './help/HelpStructuredQuery.vue'
import HelpTakingCalls from './help/HelpTakingCalls.vue'
import HelpTelephoneCpr from './help/HelpTelephoneCpr.vue'
import HelpTips from './help/HelpTips.vue'
import HelpTrainer from './help/HelpTrainer.vue'

/** One page of the help center; the router only comes here for a known slug. */
const props = defineProps<{ slug: HelpSlug }>()

/** The content of each topic, by slug. */
const CONTENT: Record<HelpSlug, Component> = {
    'erste-schritte': HelpFirstSteps,
    'notrufe-annehmen': HelpTakingCalls,
    'notrufabfrage': HelpStructuredQuery,
    'telefonreanimation': HelpTelephoneCpr,
    'ausbilder': HelpTrainer,
    'anrufer-spielen': HelpPlayingTheCaller,
    'auswertung': HelpDebrief,
    'tipps': HelpTips,
}

const {t} = useI18n()
const topics = useHelpTopics()
const topic = computed(() => topics.value.find(candidate => candidate.slug === props.slug)!)

usePage(() => ({
    title: t('hilfe.topicPageTitle', {topic: topic.value.title}),
    description: topic.value.description,
    path: helpPath(topic.value.slug),
    structuredData: [breadcrumbData([
        {name: t('app.name'), path: '/'},
        {name: t('hilfe.breadcrumb'), path: helpPath()},
        {name: topic.value.title, path: helpPath(topic.value.slug)},
    ])],
}))
</script>

<template>
    <ToolHeader :role="t('hilfe.titel')"/>
    <HelpPage :title="topic.title" :topics="topics" :current="topic.slug">
        <component :is="CONTENT[props.slug]"/>
    </HelpPage>
</template>
