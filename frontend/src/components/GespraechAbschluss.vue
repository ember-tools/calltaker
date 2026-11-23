<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{offen: string[]}>()
const emit = defineEmits<{beenden: []}>()

const {t} = useI18n()
const liste = computed(() => props.offen.map(schluessel => t(schluessel)).join(', '))
</script>

<template>
    <div class="flex flex-wrap items-center gap-3 rounded-lg border border-rand bg-slate-50 px-4 py-3">
        <span v-if="offen.length" class="text-sm text-gedaempft">{{ t('abschluss.noch') }} <b>{{ liste }}</b></span>
        <span v-else class="text-sm font-semibold text-ok">{{ t('abschluss.vollstaendig') }}</span>
        <button type="button" :class="['ml-auto h-11 rounded-md px-5 font-bold', offen.length ? 'border border-slate-400 bg-slate-200 text-gedaempft' : 'bg-akzent text-white']" @click="emit('beenden')">{{ t('abschluss.beenden') }}</button>
    </div>
</template>
