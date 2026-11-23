<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Antwort} from '../modell/abfragegraph'

const props = defineProps<{antworten: Antwort[], zusaetze: Map<string, string>, farbe?: string}>()
const emit = defineEmits<{waehlen: [antwortId: string]}>()

/** How long a typed digit waits for a second one, so "1" then "0" picks tile 10. */
const ZIFFER_WARTEN_MS = 600

const {t} = useI18n()
const suche = ref('')
const ziffern = ref('')
let zeitgeber: ReturnType<typeof setTimeout> | undefined

const nummeriert = computed(() => props.antworten.map((antwort, nummer) => ({antwort, nummer})))
const sichtbar = computed(() => {
    const text = suche.value.trim().toLowerCase()
    return text ? nummeriert.value.filter(({antwort}) => antwort.label.toLowerCase().includes(text)) : nummeriert.value
})
const markiert = computed(() => (ziffern.value ? Number(ziffern.value) : sichtbar.value.length === 1 ? sichtbar.value[0]!.nummer : -1))

watch(() => props.antworten, () => {
    suche.value = ''
    ziffern.value = ''
})

function waehlen(nummer: number): void {
    clearTimeout(zeitgeber)
    ziffern.value = ''
    const antwort = props.antworten[nummer]
    if (antwort) emit('waehlen', antwort.id)
}

const raster = ref<HTMLElement | null>(null)

/** Puts the focus on the first tile, so digits can be typed straight away. */
function fokussieren(): void {
    raster.value?.querySelector<HTMLElement>('button, input')?.focus()
}

defineExpose({fokussieren})

/**
 * Reads digits and Enter while the tiles have the focus; a full match picks at once.
 *
 * @param ereignis the key pressed
 */
function taste(ereignis: KeyboardEvent): void {
    if (ereignis.target instanceof HTMLInputElement && !/^\d$/.test(ereignis.key)) {
        if (ereignis.key === 'Enter' && markiert.value >= 0) waehlen(markiert.value)
        return
    }
    if (/^\d$/.test(ereignis.key)) {
        ereignis.preventDefault()
        ziffern.value += ereignis.key
        clearTimeout(zeitgeber)
        const nummer = Number(ziffern.value)
        if (ziffern.value === '0' || nummer * 10 >= props.antworten.length) waehlen(nummer)
        else zeitgeber = setTimeout(() => waehlen(nummer), ZIFFER_WARTEN_MS)
    } else if (ereignis.key === 'Enter' && markiert.value >= 0) {
        ereignis.preventDefault()
        waehlen(markiert.value)
    }
}
</script>

<template>
    <div ref="raster" class="flex flex-col gap-3">
        <label v-if="antworten.length > 9" class="flex items-center gap-2 text-xs font-semibold text-gedaempft">
            {{ t('sna.suche') }}
            <input v-model="suche" :placeholder="t('sna.sucheHinweis')" class="h-8 max-w-sm flex-1 rounded border border-slate-400 px-2 text-sm text-tinte" @keydown="taste"/>
        </label>
        <p v-else class="m-0 text-xs text-gedaempft">{{ t('sna.sucheHinweis') }}</p>
        <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-3">
            <button
                v-for="{antwort, nummer} in sichtbar"
                :key="antwort.id"
                type="button"
                :class="['flex min-h-16 items-stretch overflow-hidden rounded-md border p-0 text-left font-semibold', (antwort.farbe ?? farbe) === 'fw' ? 'border-red-300 bg-red-100 text-red-950' : 'border-sky-300 bg-sky-100 text-sky-950', nummer === markiert ? 'outline-3 outline-offset-1 outline-slate-900' : '']"
                @click="waehlen(nummer)"
                @keydown="taste"
            >
                <span :class="['flex w-11 flex-none items-center justify-center font-mono', (antwort.farbe ?? farbe) === 'fw' ? 'bg-red-300' : 'bg-sky-300']">{{ nummer }}</span>
                <span class="flex flex-1 flex-col justify-center px-3 py-2 leading-tight">
                    {{ antwort.label }}
                    <small v-if="zusaetze.get(antwort.id)" class="font-mono font-normal opacity-75">{{ zusaetze.get(antwort.id) }}</small>
                </span>
            </button>
        </div>
    </div>
</template>
