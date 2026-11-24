<script setup lang="ts">
import {faCheck, faCopy, faXmark} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {onBeforeUnmount, ref} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{titel: string, code: string}>()

/** How long the copy result stays visible. */
const ANZEIGE_MS = 1500

const {t} = useI18n()
const ergebnis = ref<'kopiert' | 'fehler' | null>(null)
let zeitgeber: ReturnType<typeof setTimeout> | undefined

/** Copies the code and shows for a moment whether that worked. */
async function kopieren(): Promise<void> {
    try {
        if (!navigator.clipboard) throw new Error('keine Zwischenablage')
        await navigator.clipboard.writeText(props.code)
        ergebnis.value = 'kopiert'
    } catch {
        ergebnis.value = 'fehler'
    }
    clearTimeout(zeitgeber)
    zeitgeber = setTimeout(() => {
        ergebnis.value = null
    }, ANZEIGE_MS)
}

onBeforeUnmount(() => clearTimeout(zeitgeber))
</script>

<template>
    <span :class="['flex items-center gap-2 rounded-md border py-1 pl-2.5 pr-1.5 transition-colors', ergebnis === 'kopiert' ? 'border-green-400 bg-green-950' : ergebnis === 'fehler' ? 'border-red-400 bg-red-950' : 'border-slate-600']">
        <span class="text-xs text-slate-300">{{ titel }}</span>
        <span class="font-mono">{{ code }}</span>
        <button type="button" :class="['rounded px-2 py-0.5 text-xs', ergebnis === 'kopiert' ? 'bg-green-600' : ergebnis === 'fehler' ? 'bg-red-700' : 'bg-slate-700']" :aria-label="t('codes.kopieren', {code})" @click="kopieren">
            <FontAwesomeIcon :icon="ergebnis === 'kopiert' ? faCheck : ergebnis === 'fehler' ? faXmark : faCopy" aria-hidden="true"/>
            <span v-if="ergebnis" class="ml-1">{{ t(`codes.${ergebnis}`) }}</span>
        </button>
        <span class="sr-only" role="status"><template v-if="ergebnis">{{ t(`codes.${ergebnis}`) }}</template></span>
    </span>
</template>
