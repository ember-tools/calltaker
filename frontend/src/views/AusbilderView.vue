<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import CodeAnzeige from '../components/CodeAnzeige.vue'
import GetrenntHinweis from '../components/GetrenntHinweis.vue'
import KopfLeiste from '../components/KopfLeiste.vue'
import PoolDatei from '../components/PoolDatei.vue'
import UnbekannteUebung from '../components/UnbekannteUebung.vue'
import VerbindungsZeichen from '../components/VerbindungsZeichen.vue'
import {useUebung} from '../composables/useUebung'

const props = defineProps<{code: string}>()

const {t} = useI18n()
const {zustand, erreichbar, unbekannt, absicht} = useUebung<'ausbilder'>(props.code)
</script>

<template>
    <div class="min-h-screen">
        <KopfLeiste :rolle="t('ausbilder.titel')">
            <template v-if="zustand">
                <CodeAnzeige :titel="t('codes.ausbilder')" :code="zustand.codes.ausbilder"/>
                <CodeAnzeige :titel="t('codes.trainee')" :code="zustand.codes.trainee"/>
                <VerbindungsZeichen :name="t('verbindung.trainee')" :verbunden="zustand.verbunden.trainee"/>
            </template>
        </KopfLeiste>
        <GetrenntHinweis v-if="!erreichbar"/>
        <UnbekannteUebung v-if="unbekannt"/>
        <main v-else class="p-5">
            <p v-if="!zustand" class="m-0 text-gedaempft">{{ t('allgemein.laden') }}</p>
            <section v-else class="flex max-w-xl flex-col gap-3 rounded-lg border border-rand bg-flaeche p-4">
                <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('ausbilder.pool') }}</h2>
                <p v-if="zustand.pool.length === 0" class="m-0 text-sm text-gedaempft">{{ t('ausbilder.poolLeer') }}</p>
                <template v-else>
                    <p class="m-0 text-sm">{{ zustand.pool.length === 1 ? t('ausbilder.poolEins') : t('ausbilder.poolAnzahl', {anzahl: zustand.pool.length}) }}</p>
                    <ul class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
                        <li v-for="szenario in zustand.pool" :key="szenario.id">{{ szenario.titel }}</li>
                    </ul>
                </template>
                <PoolDatei :code="code" :absicht="absicht"/>
            </section>
        </main>
    </div>
</template>
