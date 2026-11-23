<script setup lang="ts">
import {faCopy} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
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
            <FontAwesomeIcon :icon="faCopy" aria-hidden="true"/>
        </button>
    </span>
</template>
