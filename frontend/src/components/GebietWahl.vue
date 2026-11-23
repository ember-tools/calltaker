<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {ladeGebiete, type Gebiet} from '../api/gebiete'
import {BESCHRIFTUNG, FELD} from './formular'

const gebiet = defineModel<Gebiet>({required: true})
const emit = defineEmits<{geladen: [vorhanden: boolean]}>()

const {t} = useI18n()
const gebiete = ref<Record<string, string[]>>({})

onMounted(async () => {
    gebiete.value = await ladeGebiete()
    emit('geladen', Object.keys(gebiete.value).length > 0)
})

const wert = computed({
    get: () => (gebiet.value.ortsteil ? `o:${gebiet.value.ortsteil}` : gebiet.value.bezirk ? `b:${gebiet.value.bezirk}` : ''),
    set: (neu: string) => {
        gebiet.value = {bezirk: neu.startsWith('b:') ? neu.slice(2) : '', ortsteil: neu.startsWith('o:') ? neu.slice(2) : ''}
    },
})
</script>

<template>
    <label :class="BESCHRIFTUNG">{{ t('gebiet.titel') }}
        <select v-model="wert" :class="FELD">
            <option value="">{{ t('gebiet.berlin') }}</option>
            <optgroup v-for="(ortsteile, bezirk) in gebiete" :key="bezirk" :label="bezirk">
                <option :value="`b:${bezirk}`">{{ t('gebiet.ganzerBezirk', {bezirk}) }}</option>
                <option v-for="ortsteil in ortsteile" :key="ortsteil" :value="`o:${ortsteil}`">{{ ortsteil }}</option>
            </optgroup>
        </select>
    </label>
</template>
