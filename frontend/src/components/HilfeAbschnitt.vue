<script setup lang="ts">
defineProps<{titel: string}>()
</script>

<template>
    <section :aria-label="titel" class="flex flex-col gap-4 rounded-lg border border-rand bg-flaeche p-5">
        <h2 class="m-0 text-lg font-bold">{{ titel }}</h2>
        <slot/>
    </section>
</template>
