<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import VerbindungsZeichen from '../components/VerbindungsZeichen.vue'
import {useUebung} from '../composables/useUebung'

const props = defineProps<{code: string}>()

const {t} = useI18n()
const {zustand, erreichbar, unbekannt} = useUebung<'trainee'>(props.code)
</script>

<template>
    <div class="min-h-screen">
        <KopfLeiste :rolle="t('trainee.titel')">
            <VerbindungsZeichen v-if="zustand" class="ml-auto" :name="t('verbindung.ausbilder')" :verbunden="zustand.verbunden.ausbilder"/>
        </KopfLeiste>
        <GetrenntHinweis v-if="!erreichbar"/>
        <UnbekannteUebung v-if="unbekannt"/>
        <main v-else class="p-5">
            <p class="m-0 text-gedaempft">{{ zustand ? t('trainee.warten') : t('allgemein.laden') }}</p>
        </main>
    </div>
</template>
