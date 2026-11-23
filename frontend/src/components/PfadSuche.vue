<script setup lang="ts">
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph, Endpunkt} from '../modell/abfragegraph'
import {sucheEndpunkte} from '../modell/szenarioentwurf'
import {BESCHRIFTUNG, FELD} from './formular'

const props = defineProps<{graph: Abfragegraph}>()
const emit = defineEmits<{endpunkt: [endpunkt: Endpunkt]}>()

const {t} = useI18n()
const text = ref('')
const treffer = computed(() => sucheEndpunkte(props.graph, text.value))

function ersten(): void {
    if (treffer.value[0]) waehlen(treffer.value[0])
}

function waehlen(endpunkt: Endpunkt): void {
    text.value = ''
    emit('endpunkt', endpunkt)
}
</script>

<template>
    <div class="flex flex-col gap-1">
        <label :class="BESCHRIFTUNG">
            {{ t('editor.codeSuche') }}
            <input v-model="text" type="search" :placeholder="t('editor.codeSucheHinweis')" :class="FELD" @keydown.enter.prevent="ersten"/>
        </label>
        <ul v-if="treffer.length" class="m-0 flex max-h-56 list-none flex-col overflow-auto rounded border border-rand p-0">
            <li v-for="endpunkt in treffer" :key="endpunkt.knoten">
                <button type="button" class="flex w-full gap-2 border-b border-rand px-2 py-1 text-left text-sm hover:bg-slate-100" @click="waehlen(endpunkt)">
                    <span class="font-mono font-bold">{{ endpunkt.code }}</span>
                    <span class="flex-1">{{ endpunkt.anlass }}</span>
                    <span class="text-gedaempft">{{ endpunkt.kategorie }}</span>
                </button>
            </li>
        </ul>
        <p v-else-if="text.trim()" class="m-0 text-xs text-gedaempft">{{ t('editor.keinCode') }}</p>
    </div>
</template>
