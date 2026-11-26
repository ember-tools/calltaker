<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{name: string, verbunden: boolean}>()

const {t} = useI18n()
const zustand = computed(() => t(props.verbunden ? 'verbindung.verbunden' : 'verbindung.nichtVerbunden'))
</script>

<template>
    <span class="flex items-center gap-1.5 text-sm text-muted">
        <span :class="['size-2 rounded-full', verbunden ? 'bg-success' : 'bg-accented']" aria-hidden="true"/>
        {{ name }}: {{ zustand }}
    </span>
</template>
