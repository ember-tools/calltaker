<script setup lang="ts">
import {computed, ref} from 'vue'
import type {Abfragegraph} from '../modell/abfragegraph'
import {endergebnis, type Ergebnis} from '../modell/abfrageweg'
import type {Eintraege} from '../modell/eintraege'
import {leererFensterzustand, type Fensterzustand} from '../modell/fensterzustand'
import type {AnrufSicht} from '../modell/uebung'
import {phasenstand} from '../phasen/register'
import EinsatzMaske from './EinsatzMaske.vue'
import HinweisListe from './HinweisListe.vue'
import ReanimationsLeiste from './ReanimationsLeiste.vue'
import SchrittLeiste from './SchrittLeiste.vue'
import SnaFenster from './SnaFenster.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, anruf: AnrufSicht, ruhig?: boolean}>()
const eintraege = defineModel<Eintraege>({required: true})
const suche = defineModel<string>('suche', {default: ''})
const ui = defineModel<Fensterzustand>('ui', {default: leererFensterzustand})
const emit = defineEmits<{sofort: []}>()

const staende = computed(() => phasenstand(eintraege.value, {graph: props.graph, anruf: props.anruf}))
const aktivePhase = computed(() => staende.value.find(stand => stand.fehlend.length > 0)?.phase.id ?? '')
const ergebnis = computed(() => endergebnis(props.graph, eintraege.value.abfrage))
const alter = computed(() => eintraege.value.abfrage.pfad.find(schritt => schritt.knoten === 'rd.alter')?.wert)
const sna = ref<InstanceType<typeof SnaFenster> | null>(null)
const maske = ref<InstanceType<typeof EinsatzMaske> | null>(null)
const hinweise = ref<InstanceType<typeof HinweisListe> | null>(null)

/** Puts the focus on the instructions to the caller. */
function hinweiseZeigen(): void {
    hinweise.value?.fokussieren()
}

/** Puts the focus into the entry mask. */
function maskeZeigen(): void {
    maske.value?.fokussieren()
}

/** Puts the focus into the questioning window. */
function snaZeigen(): void {
    sna.value?.fokussieren()
}

defineExpose({snaZeigen, maskeZeigen, hinweiseZeigen})
</script>

<template>
    <div class="flex flex-col gap-3">
        <SchrittLeiste :staende="staende" :aktiv="aktivePhase"/>
        <div class="flex flex-wrap gap-4">
            <EinsatzMaske ref="maske" v-model="eintraege" v-model:suche="suche" class="max-w-lg min-w-0 flex-[1_1_26rem]" :anruf="anruf" :ruhig="ruhig" :stichwort="ergebnis ? `${ergebnis.code} · ${ergebnis.kategorie}` : ''" :alter="alter" @sna="snaZeigen" @sofort="emit('sofort')"/>
            <div class="flex min-w-0 flex-[999_1_36rem] flex-col gap-3">
                <ReanimationsLeiste v-model="eintraege" :graph="graph" :ruhig="ruhig" @sofort="emit('sofort')"/>
                <SnaFenster ref="sna" v-model="eintraege.abfrage" v-model:ui="ui" :graph="graph" :schwerste="schwerste" :gesperrt="!eintraege.ort.koordinaten" :seit="anruf.angenommenUm" @sofort="emit('sofort')"/>
                <HinweisListe ref="hinweise" v-model="eintraege" :graph="graph" @sofort="emit('sofort')"/>
            </div>
        </div>
    </div>
</template>
