<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import DebriefAnsicht from '../components/DebriefAnsicht.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import Rueckweg from '../components/Rueckweg.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import {useAbfragegraph} from '../composables/useAbfragegraph'
import {useAuswertung} from '../composables/useAuswertung'
import {useUebung} from '../composables/useUebung'
import type {Rolle} from '../modell/uebung'

const props = defineProps<{code: string, anrufId: string, rolle: Rolle}>()

const {t} = useI18n()
const {zustand, unbekannt} = useUebung<Rolle>(props.code)
const {graph, fehler} = useAbfragegraph()
const {ausgewertet} = useAuswertung(zustand, props.rolle)
const eintrag = computed(() => ausgewertet.value.find(a => a.anruf.id === props.anrufId))
</script>

<template>
    <div class="min-h-screen">
        <KopfLeiste :rolle="t('debrief.titel')">
            <Rueckweg :code="code" :rolle="rolle"/>
        </KopfLeiste>
        <UnbekannteUebung v-if="unbekannt"/>
        <main v-else class="mx-auto max-w-4xl p-5">
            <p v-if="fehler" role="alert" class="m-0 text-fehler">{{ t('trainee.graphFehlt', {fehler}) }}</p>
            <p v-else-if="!zustand || !graph" class="m-0 text-gedaempft">{{ t('allgemein.laden') }}</p>
            <DebriefAnsicht v-else-if="eintrag" :graph="graph" :anruf="eintrag.anruf" :szenario="eintrag.szenario" :ziele="eintrag.ziele"/>
            <p v-else class="m-0 text-gedaempft">{{ t('debrief.keiner') }}</p>
        </main>
    </div>
</template>
