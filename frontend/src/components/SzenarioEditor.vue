<script setup lang="ts">
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Ergebnis} from '../modell/abfrageweg'
import type {Ortsangabe} from '../modell/ort'
import {fehltZumSpeichern, type Entwurf} from '../modell/szenarioentwurf'
import type {Befund, Ort} from '../modell/szenario'
import EditorAnrufer from './EditorAnrufer.vue'
import {BESCHRIFTUNG, FELD} from './formular'
import OrtWahl from './OrtWahl.vue'
import PfadWahl from './PfadWahl.vue'

const props = defineProps<{graph: Abfragegraph, schwerste: Map<string, Ergebnis>, befunde: Befund[], fehler: string, hinweis: string}>()
const entwurf = defineModel<Entwurf>({required: true})
const emit = defineEmits<{speichern: [], abbrechen: []}>()

const {t} = useI18n()
const suche = ref('')
const ORTSFELDER: (keyof Pick<Ort, 'geschoss' | 'klingel' | 'anfahrt' | 'gefahren'>)[] = ['geschoss', 'klingel', 'anfahrt', 'gefahren']

const ort = computed<Ortsangabe>({
    get: () => entwurf.value.ort,
    set: neu => {
        entwurf.value.ort = {...entwurf.value.ort, ...neu}
    },
})
const fehlt = computed(() => fehltZumSpeichern(entwurf.value))
const allgemein = computed(() => props.befunde.filter(b => !b.knoten))
</script>

<template>
    <form class="flex flex-col gap-3" :aria-label="t('editor.titel')" @submit.prevent="fehlt.length === 0 && emit('speichern')">
        <ul v-if="allgemein.length" class="m-0 pl-5 text-sm text-warnung" role="alert">
            <li v-for="befund in allgemein" :key="befund.meldung">{{ befund.meldung }}</li>
        </ul>
        <label :class="BESCHRIFTUNG">{{ t('editor.szenarioTitel') }}<input v-model="entwurf.titel" :placeholder="t('editor.titelBeispiel')" :class="FELD"/></label>
        <fieldset class="m-0 flex flex-col gap-2 rounded border border-rand p-3">
            <legend class="px-1 text-sm font-bold">{{ t('editor.ort') }}</legend>
            <OrtWahl v-model="ort" v-model:text="suche"/>
            <div class="grid grid-cols-2 gap-2">
                <label :class="['col-span-2', BESCHRIFTUNG]">{{ t('maske.objekt') }}<input v-model="entwurf.ort.objekt" :class="FELD"/></label>
                <label v-for="feld in ORTSFELDER" :key="feld" :class="BESCHRIFTUNG">{{ t(`maske.${feld}`) }}<input v-model="entwurf.ort[feld]" :class="FELD"/></label>
            </div>
        </fieldset>
        <EditorAnrufer v-model="entwurf"/>
        <fieldset class="m-0 flex flex-col gap-2 rounded border border-rand p-3">
            <legend class="px-1 text-sm font-bold">{{ t('editor.pfad') }}</legend>
            <PfadWahl v-model:antworten="entwurf.antworten" v-model:ziel="entwurf.ziel" :graph="graph" :schwerste="schwerste" :befunde="befunde"/>
        </fieldset>
        <p v-if="hinweis" class="m-0 text-sm text-warnung" role="status">{{ hinweis }}</p>
        <p v-if="fehler" class="m-0 text-sm text-fehler" role="alert">{{ fehler }}</p>
        <p v-if="fehlt.length" class="m-0 text-sm text-gedaempft">{{ t('editor.nochOffen', {liste: fehlt.map(schluessel => t(schluessel)).join(', ')}) }}</p>
        <div class="flex gap-2">
            <button type="submit" :disabled="fehlt.length > 0" class="rounded bg-tinte px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-40">{{ t('editor.speichern') }}</button>
            <button type="button" class="rounded border border-slate-400 px-4 py-1.5 text-sm font-semibold" @click="emit('abbrechen')">{{ t('editor.abbrechen') }}</button>
        </div>
    </form>
</template>
