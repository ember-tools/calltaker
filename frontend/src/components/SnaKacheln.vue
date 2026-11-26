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
    rd: {kachel: 'border-info/50 bg-info/15 text-info', nummer: 'bg-info/30'},
    brand: {kachel: 'border-error/40 bg-error/15 text-error', nummer: 'bg-error/30'},
    fw: {kachel: 'border-error/40 bg-error/15 text-error', nummer: 'bg-error/30'},
    th: {kachel: 'border-warning/50 bg-warning/15 text-warning', nummer: 'bg-warning/30'},
}

/**
 * How the guidance questions mark a tile: suggested ones stand out, ones they ruled out are
 * dimmed but stay clickable.
 *
 * @param antwort the answer
 * @returns the classes for its state
 */
function leitklasse(antwort: Antwort): string {
    if (props.vorgeschlagen.includes(antwort.id)) return 'ring-3 ring-info ring-offset-1'
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
const markiert = computed(() => (ziffern.value ? Number(ziffern.value) - 1 : sichtbar.value.length === 1 ? sichtbar.value[0]!.nummer : -1))

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
 * Reads digits and Enter while the tiles have the focus; a full match picks at once. Tiles are
 * numbered from 1, so a leading 0 is ignored. Keys with Alt, Ctrl or Cmd belong to others, such as
 * the guidance questions.
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
        if (!ziffern.value && ereignis.key === '0') return
        ziffern.value += ereignis.key
        clearTimeout(zeitgeber)
        const nummer = Number(ziffern.value)
        if (nummer * 10 > alle.value.length) waehlen(nummer - 1)
        else zeitgeber = setTimeout(() => waehlen(nummer - 1), ZIFFER_WARTEN_MS)
    } else if (ereignis.key === 'Enter' && markiert.value >= 0) {
        ereignis.preventDefault()
        waehlen(markiert.value)
    }
}
</script>

<template>
    <div ref="raster" class="flex flex-col gap-3">
        <label v-if="antworten.length + weitere.length > 9" class="flex items-center gap-2 text-xs font-semibold text-muted">
            {{ t('sna.suche') }}
            <input v-model="suche" :placeholder="t('sna.sucheHinweis')" class="native-field max-w-sm flex-1" @keydown="taste"/>
        </label>
        <p v-else class="m-0 text-xs text-muted">{{ t('sna.sucheHinweis') }}</p>
        <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-3">
            <button
                v-for="{antwort, nummer} in sichtbar"
                :key="antwort.id"
                type="button"
                :class="['flex min-h-16 items-stretch overflow-hidden rounded-md border p-0 text-left font-semibold', farbeVon(antwort).kachel, nummer === markiert ? 'outline-3 outline-offset-1 outline-(--ui-text-highlighted)' : '', leitklasse(antwort)]"
                @click="waehlen(nummer)"
                @keydown="taste"
            >
                <span :class="['flex w-11 flex-none items-center justify-center font-mono', farbeVon(antwort).nummer]">{{ nummer + 1 }}</span>
                <span class="flex flex-1 flex-col justify-center px-3 py-2 leading-tight">
                    {{ antwort.label }}
                    <small v-if="zusaetze.get(antwort.id)" class="font-mono font-normal opacity-75">{{ zusaetze.get(antwort.id) }}</small>
                </span>
            </button>
        </div>
        <UButton v-if="weitere.length && !suche.trim()" color="neutral" variant="link" size="sm" class="self-start" :aria-expanded="weitereOffen" @click="weitereOffen = !weitereOffen" @keydown="taste">
            {{ weitereOffen ? t('sna.weitereZu') : t('sna.weitere', {anzahl: weitere.length}) }}
        </UButton>
    </div>
</template>
