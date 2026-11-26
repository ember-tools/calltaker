<script setup lang="ts">
import {HelpSection, HelpTopic} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'
import EinsatzMaske from '../../components/EinsatzMaske.vue'
import SchrittLeiste from '../../components/SchrittLeiste.vue'
import WarntafelFeld from '../../components/WarntafelFeld.vue'
import WarteschlangeLeiste from '../../components/WarteschlangeLeiste.vue'
import {useHelpExamples} from '../../composables/useHelpExamples'
import {useHelpTexts} from '../../composables/useHelpTopics'

/** Help topic: taking a call, from the queue to the hand-over. */
const {t} = useI18n()
const texts = useHelpTexts()
const {queue, call, entries, plate, phases, activePhase} = useHelpExamples()
const KEYS = ['F2', 'F3', 'F4', 'F9', 'Alt+Ziffer'] as const
</script>

<template>
    <HelpSection :title="t('hilfe.trainee.schlangeTitel')">
        <HelpTopic :paragraphs="texts('trainee.schlange')" :mockup="t('hilfe.trainee.schlangeMockup')">
            <div class="rounded-sm bg-default p-3"><WarteschlangeLeiste :zustand="queue" quiet/></div>
        </HelpTopic>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.maskeTitel')">
        <HelpTopic :paragraphs="texts('trainee.maske', 'trainee.funkzelle')" :mockup="entries ? t('hilfe.trainee.maskeMockup') : undefined">
            <template v-if="entries">
                <SchrittLeiste :staende="phases" :aktiv="activePhase" class="mb-3"/>
                <EinsatzMaske :model-value="entries" :anruf="call" ruhig class="max-w-lg"/>
            </template>
        </HelpTopic>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.tafelTitel')">
        <HelpTopic :paragraphs="texts('trainee.tafel')" :mockup="t('hilfe.trainee.tafelMockup')">
            <WarntafelFeld v-model="plate"/>
        </HelpTopic>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.uebergabeTitel')">
        <HelpTopic :paragraphs="texts('trainee.uebergabe', 'trainee.beenden')"/>
    </HelpSection>
    <HelpSection :title="t('hilfe.trainee.tastenTitel')">
        <HelpTopic :paragraphs="[]">
            <template #content>
                <dl class="m-0 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
                    <template v-for="key in KEYS" :key="key">
                        <dt><kbd class="rounded border border-accented bg-default px-1.5 font-mono">{{ key }}</kbd></dt>
                        <dd class="m-0 text-muted">{{ t(`hilfe.trainee.taste.${key}`) }}</dd>
                    </template>
                </dl>
            </template>
        </HelpTopic>
    </HelpSection>
</template>
