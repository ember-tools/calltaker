<script setup lang="ts">
import {computed} from 'vue'
import {useGefahrstoffe} from '../composables/useGefahrstoffe'
import {stoffeZu, type Warntafel} from '../modell/gefahrstoffe'

const props = defineProps<{tafel: Warntafel}>()
const liste = useGefahrstoffe()
const name = computed(() => stoffeZu(liste.value?.stoffe ?? [], props.tafel.un).map(stoff => stoff.bezeichnung).join(' / '))
</script>

<template>
    <span><span class="font-mono font-bold">{{ tafel.gefahrenzahl || '-' }} / {{ tafel.un }}</span> {{ name }}</span>
</template>
