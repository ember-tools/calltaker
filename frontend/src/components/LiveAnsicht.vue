<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Ergebnis} from '../modell/abfrageweg'
import type {AusbilderZustand} from '../modell/uebung'
import AusbilderSchlange from './AusbilderSchlange.vue'
import EngineParameterForm from './EngineParameterForm.vue'
import OrtVergleich from './OrtVergleich.vue'
import ProtokollListe from './ProtokollListe.vue'
import SpiegelAnsicht from './SpiegelAnsicht.vue'
import WahrheitsKarte from './WahrheitsKarte.vue'

const props = defineProps<{
    zustand: AusbilderZustand
    graph: Abfragegraph
    schwerste: Map<string, Ergebnis>
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()

const {t} = useI18n()
const gewaehlt = ref<string | undefined>()
const gespraech = computed(() => props.zustand.anrufe.find(anruf => anruf.zustand === 'gespraech'))
const anruf = computed(() => props.zustand.anrufe.find(a => a.id === gewaehlt.value) ?? gespraech.value ?? props.zustand.anrufe.at(-1))

watch(() => gespraech.value?.id, id => {
    if (id) gewaehlt.value = id
}, {immediate: true})
</script>

<template>
    <div class="flex flex-col gap-4">
        <AusbilderSchlange :zustand="zustand" :absicht="absicht"/>
        <EngineParameterForm :parameter="zustand.engine.parameter" :absicht="absicht"/>
        <div class="flex flex-wrap items-start gap-4">
            <SpiegelAnsicht v-if="anruf && anruf.zustand === 'gespraech'" class="min-w-0 flex-[2_1_40rem]" :graph="graph" :schwerste="schwerste" :anruf="anruf" :spiegel="zustand.spiegel"/>
            <div class="flex min-w-0 flex-[1_1_24rem] flex-col gap-3">
                <template v-if="anruf">
                    <WahrheitsKarte :graph="graph" :anruf="anruf" :ziele="zustand.engine.ziele" @korrigieren="(anleitung, gegeben) => absicht('anleitung.korrigieren', {anrufId: anruf!.id, anleitung, gegeben})" @eintreffen="absicht('anruf.eintreffen', {anrufId: anruf!.id})"/>
                    <OrtVergleich :anruf="anruf"/>
                </template>
                <p v-else class="m-0 text-sm text-muted">{{ t('live.keinAnruf') }}</p>
                <ProtokollListe :anrufe="zustand.anrufe" :code="zustand.codes.ausbilder" :gewaehlt="anruf?.id" @waehlen="id => gewaehlt = id"/>
            </div>
        </div>
    </div>
</template>
