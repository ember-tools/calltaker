<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const props = defineProps<{titel: string, code: string}>()

const {t} = useI18n()

async function kopieren(): Promise<void> {
    await navigator.clipboard?.writeText(props.code)
}
</script>

<template>
    <span class="flex items-center gap-2 rounded-md border border-slate-600 py-1 pl-2.5 pr-1.5">
        <span class="text-xs text-slate-300">{{ titel }}</span>
        <span class="font-mono">{{ code }}</span>
        <button type="button" class="rounded bg-slate-700 px-2 py-0.5 text-xs" :aria-label="t('codes.kopieren', {code})" @click="kopieren">
            <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="9" y="9" width="12" height="12" rx="2"/>
                <path d="M5 15V5a2 2 0 0 1 2-2h10"/>
            </svg>
        </button>
    </span>
</template>
