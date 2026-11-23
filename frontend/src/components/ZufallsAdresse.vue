<script setup lang="ts">
import {ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {zufallsAdresse, type Gebiet} from '../api/gebiete'
import type {Adressvorschlag} from '../modell/ort'
import GebietWahl from './GebietWahl.vue'

const emit = defineEmits<{adresse: [vorschlag: Adressvorschlag]}>()

const {t} = useI18n()
const gebiet = ref<Gebiet>({bezirk: '', ortsteil: ''})
const fehler = ref('')
const listeDa = ref(true)

async function ziehen(): Promise<void> {
    try {
        const adresse = await zufallsAdresse(gebiet.value)
        fehler.value = adresse ? '' : listeDa.value ? t('gebiet.keineImGebiet') : t('gebiet.keineAdresse')
        if (adresse) emit('adresse', adresse)
    } catch {
        fehler.value = t('gebiet.nichtErreichbar')
    }
}
</script>

<template>
    <div class="flex flex-wrap items-end gap-2">
        <GebietWahl v-model="gebiet" @geladen="vorhanden => listeDa = vorhanden"/>
        <button type="button" class="h-8 rounded border border-slate-400 px-3 text-sm font-semibold" @click="ziehen">{{ t('gebiet.zufall') }}</button>
        <p v-if="fehler" class="m-0 text-xs text-fehler" role="alert">{{ fehler }}</p>
    </div>
</template>
