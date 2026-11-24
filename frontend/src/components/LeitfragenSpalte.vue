<script setup lang="ts">
import {faRotateLeft, faTriangleExclamation} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, nextTick, onBeforeUnmount, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Antwort} from '../modell/abfragegraph'
import type {Leitfrageneintrag} from '../modell/eintraege'
import {angeboten, type Knotenleitfragen, type Leitstand} from '../modell/leitfragen'

const props = defineProps<{eintrag: Knotenleitfragen, antworten: Antwort[], stand: Leitstand, ruhig?: boolean}>()
const gegeben = defineModel<Leitfrageneintrag[]>({default: () => []})
const emit = defineEmits<{sofort: [], waehlen: [antwortId: string]}>()

const {t} = useI18n()
const spalte = ref<HTMLElement | null>(null)
const angebot = computed(() => (props.stand.frage ? angeboten(props.stand.frage, props.stand.kacheln) : []))
const nummer = computed(() => new Map(props.antworten.map((antwort, stelle) => [antwort.id, stelle + 1])))
const label = computed(() => new Map(props.antworten.map(antwort => [antwort.id, antwort.label])))
const fragen = computed(() => new Map(props.eintrag.fragen.map(frage => [frage.id, frage.frage])))
const zeile = computed(() => {
    if (props.stand.frage) return props.stand.frage.frage
    return props.stand.vorschlag.length ? t('leitfragen.vorschlag') : t('leitfragen.keineFrage')
})

/**
 * Sets this node's answers, keeping those of other nodes. When the answer was given in the
 * column, the focus moves on to the first answer of the next question, else to the first
 * suggested tile; an answer by shortcut leaves the focus where it was, such as on the tiles.
 *
 * @param hier the node's answers, in order
 */
function setzen(hier: Leitfrageneintrag[]): void {
    const aktiv = document.activeElement
    const hierDrin = aktiv === document.body || Boolean(aktiv && spalte.value?.contains(aktiv))
    gegeben.value = [...gegeben.value.filter(g => g.knoten !== props.eintrag.knoten), ...hier]
    emit('sofort')
    if (hierDrin) void nextTick(() => spalte.value?.querySelector<HTMLElement>('[data-leitantwort], [data-vorschlag]')?.focus())
}

/**
 * Answers the question offered now.
 *
 * @param antwort the answer's label
 */
function beantworten(antwort: string): void {
    const frage = props.stand.frage
    if (!frage) return
    setzen([...props.stand.beantwortet, {knoten: props.eintrag.knoten, frage: frage.id, antwort}])
}

/**
 * Goes back to an earlier question, dropping its answer and all after it.
 *
 * @param stelle the position of the answer to take back
 */
function zurueckZu(stelle: number): void {
    setzen(props.stand.beantwortet.slice(0, stelle))
}

/**
 * Whether a key press was meant for a text field rather than for the guidance.
 *
 * @param ziel where the key was pressed
 * @returns true for inputs, text areas and editable content
 */
function imTextfeld(ziel: EventTarget | null): boolean {
    return ziel instanceof HTMLElement && (ziel.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(ziel.tagName))
}

/**
 * Answers with Alt and a digit, so the digits alone stay with the tiles. Keys typed into a text
 * field, held down, or combined with Ctrl or Cmd (AltGr, the Mac's Option characters) are left
 * alone, and so is a key the tiles already used.
 *
 * @param ereignis the key pressed
 */
function taste(ereignis: KeyboardEvent): void {
    if (props.ruhig || ereignis.defaultPrevented || ereignis.repeat || !ereignis.altKey || ereignis.ctrlKey || ereignis.metaKey) return
    if (imTextfeld(ereignis.target) || !/^Digit[1-9]$/.test(ereignis.code)) return
    const antwort = angebot.value[Number(ereignis.code.slice(5)) - 1]
    if (!antwort) return
    ereignis.preventDefault()
    beantworten(antwort.label)
}

onMounted(() => window.addEventListener('keydown', taste))
onBeforeUnmount(() => window.removeEventListener('keydown', taste))
</script>

<template>
    <aside ref="spalte" :aria-label="t('leitfragen.titel')" class="flex flex-col gap-2 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm">
        <h4 class="m-0 text-sm font-bold text-sky-900">{{ t('leitfragen.titel') }}</h4>
        <div :class="['flex flex-col gap-2 rounded p-2', stand.frage?.sicherheit ? 'border-2 border-red-600 bg-red-50' : 'bg-white']">
            <p role="status" :class="['m-0 text-base font-semibold', stand.frage?.sicherheit ? 'text-red-900' : 'text-sky-950']">
                <span v-if="stand.frage?.sicherheit" role="img" :aria-label="t('leitfragen.sicherheit')" class="mr-1.5"><FontAwesomeIcon :icon="faTriangleExclamation" aria-hidden="true"/></span>{{ zeile }}
            </p>
            <p v-if="stand.frage?.hinweis" class="m-0 text-xs text-gedaempft">{{ stand.frage.hinweis }}</p>
            <div v-if="stand.frage" class="flex flex-wrap gap-1.5">
                <button v-for="(antwort, stelle) in angebot" :key="`${stand.frage.id}-${antwort.label}`" data-leitantwort type="button" :aria-keyshortcuts="`Alt+${stelle + 1}`" class="flex min-h-9 items-center gap-2 rounded border border-slate-400 bg-white px-3 font-semibold" @click="beantworten(antwort.label)">
                    {{ antwort.label }}<small class="font-mono font-normal text-gedaempft">{{ t('leitfragen.taste', {nummer: stelle + 1}) }}</small>
                </button>
            </div>
            <div v-else-if="stand.vorschlag.length" class="flex flex-col gap-1.5">
                <button v-for="id in stand.vorschlag" :key="id" data-vorschlag type="button" class="flex min-h-9 items-center gap-2 rounded border-2 border-sky-600 bg-white px-3 text-left font-semibold" @click="emit('waehlen', id)">
                    <span class="font-mono">{{ nummer.get(id) }}</span>{{ label.get(id) }}
                </button>
            </div>
        </div>
        <ol v-if="stand.beantwortet.length" :aria-label="t('leitfragen.bisher')" class="m-0 flex flex-col gap-0.5 pl-5 text-xs">
            <li v-for="(antwort, stelle) in stand.beantwortet" :key="`${stelle}-${antwort.frage}`">
                {{ fragen.get(antwort.frage) }} <b>{{ antwort.antwort }}</b>
                <button type="button" class="ml-1 underline" :aria-label="t('leitfragen.aendernFrage', {frage: fragen.get(antwort.frage)})" @click="zurueckZu(stelle)">{{ t('leitfragen.aendern') }}</button>
            </li>
        </ol>
        <button v-if="stand.beantwortet.length" type="button" class="self-start text-xs underline" @click="zurueckZu(0)"><FontAwesomeIcon :icon="faRotateLeft" class="mr-1" aria-hidden="true"/>{{ t('leitfragen.neu') }}</button>
        <p class="m-0 text-xs text-gedaempft">{{ t('leitfragen.direkt') }}</p>
    </aside>
</template>
