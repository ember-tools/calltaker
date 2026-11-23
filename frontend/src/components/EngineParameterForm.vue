<script setup lang="ts">
import {ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {EngineParameter} from '../modell/uebung'
import {BESCHRIFTUNG, FELD} from './formular'

const props = defineProps<{
    parameter: EngineParameter
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()

const {t} = useI18n()
const ZAHLEN = ['erstesKlingelnMin', 'erstesKlingelnMax', 'basisAbstand', 'abstandFaktor', 'maxSchlange', 'geduldMin', 'geduldMax'] as const
const werte = ref<EngineParameter>({...props.parameter})
const fehler = ref('')

watch(() => JSON.stringify(props.parameter), () => {
    werte.value = {...props.parameter}
})

async function setzen(): Promise<void> {
    try {
        await props.absicht('engine.parameter', {parameter: werte.value})
        fehler.value = ''
    } catch (e) {
        fehler.value = (e as Error).message
    }
}
</script>

<template>
    <details class="rounded border border-rand p-3 text-sm">
        <summary class="cursor-pointer font-bold">{{ t('parameter.titel') }}</summary>
        <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <label v-for="feld in ZAHLEN" :key="feld" :class="BESCHRIFTUNG">{{ t(`parameter.${feld}`) }}
                <input v-model.number="werte[feld]" type="number" min="0" step="any" :class="FELD" @change="setzen"/>
            </label>
            <label class="col-span-2 flex items-center gap-2"><input v-model="werte.zurueckInPool" type="checkbox" @change="setzen"/>{{ t('parameter.zurueckInPool') }}</label>
        </div>
        <p v-if="fehler" class="m-0 mt-2 text-fehler" role="alert">{{ fehler }}</p>
    </details>
</template>
