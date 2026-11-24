<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Antwort} from '../modell/abfragegraph'

const props = withDefaults(defineProps<{antworten: Antwort[], weitere?: Antwort[], zusaetze: Map<string, string>, farbe?: string, passend?: ReadonlySet<string>, vorgeschlagen?: readonly string[]}>(), {weitere: () => [], farbe: 'rd', passend: undefined, vorgeschlagen: () => []})
const emit = defineEmits<{waehlen: [antwortId: string]}>()

/** How long a typed digit waits for a second one, so "1" then "0" picks tile 10. */
const ZIFFER_WARTEN_MS = 600

const {t} = useI18n()
const suche = defineModel<string>('suche', {default: ''})
const weitereOffen = defineModel<boolean>('weitereOffen', {default: false})
const ziffern = ref('')
let zeitgeber: ReturnType<typeof setTimeout> | undefined

/** The colours of the tiles per discipline: medical blue, fire red, technical rescue amber. */
const FARBEN: Record<string, {kachel: string, nummer: string}> = {
    rd: {kachel: 'border-sky-300 bg-sky-100 text-sky-950', nummer: 'bg-sky-300'},
    brand: {kachel: 'border-red-300 bg-red-100 text-red-950', nummer: 'bg-red-300'},
    fw: {kachel: 'border-red-300 bg-red-100 text-red-950', nummer: 'bg-red-300'},
    th: {kachel: 'border-amber-300 bg-amber-100 text-amber-950', nummer: 'bg-amber-300'},
}

/**
 * How the guidance questions mark a tile: suggested ones stand out, ones they ruled out are
 * dimmed but stay clickable.
 *
 * @param antwort the answer
 * @returns the classes for its state
 */
function leitklasse(antwort: Antwort): string {
    if (props.vorgeschlagen.includes(antwort.id)) return 'ring-3 ring-sky-600 ring-offset-1'
    return props.passend && !props.passend.has(antwort.id) ? 'opacity-40' : ''
}

/**
 * The colours of a tile: its answer's own discipline, else that of the questioning.
 *
 * @param antwort the answer
 * @returns the tile's and the number's classes
 */
function farbeVon(antwort: Antwort): {kachel: string, nummer: string} {
    return FARBEN[antwort.farbe ?? props.farbe ?? 'rd'] ?? FARBEN.rd!
}

const alle = computed(() => [...props.antworten, ...props.weitere])
const nummeriert = computed(() => alle.value.map((antwort, nummer) => ({antwort, nummer})))
const sichtbar = computed(() => {
    const text = suche.value.trim().toLowerCase()
    if (text) return nummeriert.value.filter(({antwort}) => antwort.label.toLowerCase().includes(text))
    return weitereOffen.value ? nummeriert.value : nummeriert.value.slice(0, props.antworten.length)
})
const markiert = computed(() => (ziffern.value ? Number(ziffern.value) : sichtbar.value.length === 1 ? sichtbar.value[0]!.nummer : -1))

watch(() => alle.value.map(antwort => antwort.id).join('|'), () => {
    suche.value = ''
    ziffern.value = ''
    weitereOffen.value = false
})

function waehlen(nummer: number): void {
    clearTimeout(zeitgeber)
    ziffern.value = ''
    const antwort = alle.value[nummer]
    if (antwort) emit('waehlen', antwort.id)
}

const raster = ref<HTMLElement | null>(null)

/** Puts the focus on the first tile, so digits can be typed straight away. */
function fokussieren(): void {
    raster.value?.querySelector<HTMLElement>('button, input')?.focus()
}

defineExpose({fokussieren})

/**
 * Reads digits and Enter while the tiles have the focus; a full match picks at once. Keys with
 * Alt, Ctrl or Cmd belong to others, such as the guidance questions.
 *
 * @param ereignis the key pressed
 */
function taste(ereignis: KeyboardEvent): void {
    if (ereignis.altKey || ereignis.ctrlKey || ereignis.metaKey) return
    if (ereignis.target instanceof HTMLInputElement && !/^\d$/.test(ereignis.key)) {
        if (ereignis.key !== 'Enter') return
        ereignis.preventDefault()
        if (markiert.value >= 0) waehlen(markiert.value)
        return
    }
    if (/^\d$/.test(ereignis.key)) {
        ereignis.preventDefault()
        ziffern.value += ereignis.key
        clearTimeout(zeitgeber)
        const nummer = Number(ziffern.value)
        if (ziffern.value === '0' || nummer * 10 >= alle.value.length) waehlen(nummer)
        else zeitgeber = setTimeout(() => waehlen(nummer), ZIFFER_WARTEN_MS)
    } else if (ereignis.key === 'Enter' && markiert.value >= 0) {
        ereignis.preventDefault()
        waehlen(markiert.value)
    }
}
</script>

<template>
    <div ref="raster" class="flex flex-col gap-3">
        <label v-if="antworten.length + weitere.length > 9" class="flex items-center gap-2 text-xs font-semibold text-gedaempft">
            {{ t('sna.suche') }}
            <input v-model="suche" :placeholder="t('sna.sucheHinweis')" class="h-8 max-w-sm flex-1 rounded border border-slate-400 px-2 text-sm text-tinte" @keydown="taste"/>
        </label>
        <p v-else class="m-0 text-xs text-gedaempft">{{ t('sna.sucheHinweis') }}</p>
        <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-3">
            <button
                v-for="{antwort, nummer} in sichtbar"
                :key="antwort.id"
                type="button"
                :class="['flex min-h-16 items-stretch overflow-hidden rounded-md border p-0 text-left font-semibold', farbeVon(antwort).kachel, nummer === markiert ? 'outline-3 outline-offset-1 outline-slate-900' : '', leitklasse(antwort)]"
                @click="waehlen(nummer)"
                @keydown="taste"
            >
                <span :class="['flex w-11 flex-none items-center justify-center font-mono', farbeVon(antwort).nummer]">{{ nummer }}</span>
                <span class="flex flex-1 flex-col justify-center px-3 py-2 leading-tight">
                    {{ antwort.label }}
                    <small v-if="zusaetze.get(antwort.id)" class="font-mono font-normal opacity-75">{{ zusaetze.get(antwort.id) }}</small>
                </span>
            </button>
        </div>
        <button v-if="weitere.length && !suche.trim()" type="button" class="self-start text-sm underline" :aria-expanded="weitereOffen" @click="weitereOffen = !weitereOffen" @keydown="taste">
            {{ weitereOffen ? t('sna.weitereZu') : t('sna.weitere', {anzahl: weitere.length}) }}
        </button>
    </div>
</template>
