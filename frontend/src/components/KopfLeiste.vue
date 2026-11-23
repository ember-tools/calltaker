<script setup lang="ts">
import {useI18n} from 'vue-i18n'

defineProps<{rolle: string}>()

const {t} = useI18n()
</script>

<template>
    <header class="flex flex-wrap items-center gap-4 bg-leiste px-5 py-2.5 text-white">
        <div class="flex items-baseline gap-2.5">
            <span class="font-condensed text-xl font-bold tracking-wider">{{ t('app.name') }}</span>
            <span class="text-sm text-slate-300">{{ rolle }}</span>
        </div>
        <slot/>
    </header>
</template>
