<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Ergebnis} from '../modell/abfrageweg'
import type {Eintraege} from '../modell/eintraege'
import {leererFensterzustand, type Fensterzustand} from '../modell/fensterzustand'
import {sichtVon, type Anruf} from '../modell/uebung'
import GespraechsFlaeche from './GespraechsFlaeche.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, anruf: Anruf, spiegel: Record<string, unknown>}>()

const {t} = useI18n()
const sicht = computed(() => sichtVon(props.anruf))
const kopie = computed(() => JSON.parse(JSON.stringify(props.anruf.eintraege)) as Eintraege)
const suche = computed(() => String(props.spiegel.suche ?? ''))
const fenster = computed<Fensterzustand>(() => ({...leererFensterzustand(), ...props.spiegel}))
</script>

<template>
    <section :aria-label="t('spiegel.titel')" class="flex flex-col gap-2">
        <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('spiegel.titel') }}</h2>
        <p v-if="suche" class="m-0 text-sm">{{ t('spiegel.tipptSuche', {text: suche}) }}</p>
        <div inert class="origin-top-left rounded-lg border border-rand bg-white p-3 opacity-95 [zoom:0.8]">
            <GespraechsFlaeche :model-value="kopie" :suche="suche" :ui="fenster" ruhig :graph="graph" :schwerste="schwerste" :anruf="sicht"/>
        </div>
    </section>
</template>
