<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {abstandGerundet, type Kartenpunkt} from '../modell/karte'
import type {Anruf} from '../modell/uebung'
import KarteLeaflet from './KarteLeaflet.vue'

const props = defineProps<{anruf: Anruf}>()

const {t} = useI18n()
const wahr = computed(() => props.anruf.szenario.ort.koordinaten)
const erfasst = computed(() => props.anruf.eintraege.ort.koordinaten)
const punkte = computed<Kartenpunkt[]>(() => [
    ...(wahr.value ? [{breite: wahr.value[0], laenge: wahr.value[1], art: 'wahrheit' as const}] : []),
    ...(erfasst.value ? [{breite: erfasst.value[0], laenge: erfasst.value[1], art: 'erfasst' as const}] : []),
])
const abstand = computed(() => (wahr.value && erfasst.value ? abstandGerundet(wahr.value, erfasst.value) : undefined))
</script>

<template>
    <figure class="m-0 flex flex-col gap-1">
        <KarteLeaflet :punkte="punkte" :beschriftung="t('wahrheit.karte')" class="h-56"/>
        <figcaption class="text-xs text-gedaempft">
            {{ abstand === undefined ? t('wahrheit.keinPunkt') : t('wahrheit.abstand', {meter: abstand}) }} · {{ t('wahrheit.legende') }}
        </figcaption>
    </figure>
</template>
