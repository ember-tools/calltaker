<script setup lang="ts">
defineProps<{beschriftung: string}>()
</script>

<template>
    <figure class="m-0 flex flex-col gap-1.5">
        <div class="overflow-x-auto rounded-lg border border-dashed border-slate-400 bg-grund">
            <div inert class="pointer-events-none min-w-[36rem] select-none p-3">
                <slot/>
            </div>
        </div>
        <figcaption class="text-xs text-gedaempft">{{ beschriftung }}</figcaption>
    </figure>
</template>
