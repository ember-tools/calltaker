<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{name: string, verbunden: boolean}>()

const {t} = useI18n()
const zustand = computed(() => t(props.verbunden ? 'verbindung.verbunden' : 'verbindung.nichtVerbunden'))
</script>

<template>
    <span class="flex items-center gap-1.5 text-sm text-slate-300">
        <span :class="['size-2 rounded-full', verbunden ? 'bg-green-400' : 'bg-slate-500']" aria-hidden="true"/>
        {{ name }}: {{ zustand }}
    </span>
</template>
