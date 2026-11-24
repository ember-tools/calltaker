<script setup lang="ts">
import HilfeMockup from './HilfeMockup.vue'

defineProps<{titel?: string, texte: string[], mockup?: string}>()
</script>

<template>
    <div class="flex flex-col gap-2">
        <h3 v-if="titel" class="m-0 text-base font-bold">{{ titel }}</h3>
        <p v-for="text in texte" :key="text" class="m-0 leading-relaxed text-gedaempft">{{ text }}</p>
        <slot name="inhalt"/>
        <HilfeMockup v-if="mockup" :beschriftung="mockup">
            <slot/>
        </HilfeMockup>
    </div>
</template>
