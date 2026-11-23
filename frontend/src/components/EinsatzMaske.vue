<script setup lang="ts">
import {faCheck} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Eintraege} from '../modell/eintraege'
import type {Warntafel} from '../modell/gefahrstoffe'
import type {Nachtrag} from '../modell/uebergabe'
import type {Ortsangabe} from '../modell/ort'
import {anzeigen} from '../modell/rufnummer'
import type {AnrufSicht} from '../modell/uebung'
import NachtragMarke from './NachtragMarke.vue'
import OrtWahl from './OrtWahl.vue'
import WarntafelFeld from './WarntafelFeld.vue'

const props = defineProps<{anruf: AnrufSicht, stichwort?: string, alter?: string, ruhig?: boolean, warntafel?: boolean, nachgetragen?: Set<Nachtrag>}>()
const eintraege = defineModel<Eintraege>({required: true})
const suche = defineModel<string>('suche', {default: ''})
const emit = defineEmits<{sna: [], sofort: []}>()

const {t} = useI18n()
const andereGeklickt = ref(false)
const andereNummer = computed({
    get: () => andereGeklickt.value || props.anruf.rufnummerUnterdrueckt || (!eintraege.value.anrufer.rufnummerBestaetigt && eintraege.value.anrufer.rueckrufnummer !== ''),
    set: an => {
        andereGeklickt.value = an
    },
})

const ort = computed<Ortsangabe>({
    get: () => ({adresse: eintraege.value.ort.adresse, koordinaten: eintraege.value.ort.koordinaten, objekt: eintraege.value.ort.objekt}),
    set: wert => {
        eintraege.value.ort = {...eintraege.value.ort, ...wert}
        if (wert.koordinaten) emit('sofort')
    },
})

const tafel = computed<Warntafel>({
    get: () => eintraege.value.ort.gefahrgut ?? {un: '', gefahrenzahl: ''},
    set: wert => {
        eintraege.value.ort = {...eintraege.value.ort, gefahrgut: wert}
    },
})

const ORTSFELDER = ['geschoss', 'klingel', 'anfahrt', 'gefahren'] as const

function bestaetigen(): void {
    eintraege.value.anrufer = {...eintraege.value.anrufer, rufnummerBestaetigt: true, rueckrufnummer: props.anruf.rufnummer ?? ''}
    andereNummer.value = false
    emit('sofort')
}

function andere(): void {
    eintraege.value.anrufer = {...eintraege.value.anrufer, rufnummerBestaetigt: false, rueckrufnummer: ''}
    andereNummer.value = true
}

const wurzel = ref<HTMLElement | null>(null)

/** Puts the focus into the address search, where every call starts. */
function fokussieren(): void {
    wurzel.value?.querySelector<HTMLElement>('[role=combobox]')?.focus()
}

onMounted(fokussieren)

defineExpose({fokussieren})
</script>

<template>
    <section ref="wurzel" :aria-label="t('maske.titel')" class="flex flex-col gap-3 rounded-lg border border-rand bg-flaeche p-3.5">
        <h2 class="m-0 font-condensed text-base font-bold tracking-wider text-gedaempft">{{ t('maske.titel') }}</h2>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.mitteiler') }}<NachtragMarke v-if="nachgetragen?.has('anrufer')"/></legend>
            <div class="grid grid-cols-2 gap-2">
                <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('maske.name') }}
                    <input v-model="eintraege.anrufer.name" class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
                </label>
                <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('maske.telefon') }}
                    <input :value="anruf.rufnummer ? anzeigen(anruf.rufnummer) : t('warteschlange.unterdrueckt')" readonly class="h-8 w-full min-w-0 rounded border border-slate-300 bg-slate-100 px-2 font-mono text-sm text-tinte"/>
                </label>
            </div>
            <div v-if="!anruf.rufnummerUnterdrueckt" class="flex flex-wrap gap-2">
                <button type="button" :class="['h-8 rounded border px-3 text-sm font-semibold', eintraege.anrufer.rufnummerBestaetigt ? 'border-ok bg-green-50 text-ok' : 'border-akzent bg-sky-50 text-akzent']" @click="bestaetigen">
                    <FontAwesomeIcon v-if="eintraege.anrufer.rufnummerBestaetigt" :icon="faCheck" class="mr-1" aria-hidden="true"/>
                    {{ eintraege.anrufer.rufnummerBestaetigt ? t('maske.bestaetigt') : t('maske.bestaetigen') }}
                </button>
                <button type="button" class="h-8 rounded border border-slate-400 px-3 text-sm font-semibold" @click="andere">{{ t('maske.andere') }}</button>
            </div>
            <label v-if="andereNummer" class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                {{ t('maske.rueckruf') }}
                <input v-model="eintraege.anrufer.rueckrufnummer" inputmode="tel" class="h-8 rounded border border-slate-400 px-2 font-mono text-sm text-tinte"/>
            </label>
        </fieldset>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.einsatzort') }}<NachtragMarke v-if="nachgetragen?.has('ort')"/></legend>
            <OrtWahl v-model="ort" v-model:text="suche" :ruhig="ruhig"/>
            <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                {{ t('maske.objekt') }}
                <input v-model="eintraege.ort.objekt" class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
            </label>
            <div class="grid grid-cols-2 gap-2">
                <label v-for="feld in ORTSFELDER" :key="feld" class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t(`maske.${feld}`) }}
                    <input v-model="eintraege.ort[feld]" class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
                </label>
            </div>
        </fieldset>
        <WarntafelFeld v-if="warntafel || tafel.un || tafel.gefahrenzahl" v-model="tafel"/>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.ereignis') }}</legend>
            <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto] items-end gap-2">
                <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    <span>{{ t('maske.stichwort') }}<NachtragMarke v-if="nachgetragen?.has('code')"/></span>
                    <input :value="stichwort ?? ''" readonly class="h-8 w-full min-w-0 rounded border border-slate-300 bg-slate-100 px-2 font-mono text-sm text-tinte"/>
                </label>
                <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('maske.alter') }}
                    <input :value="alter ?? ''" readonly class="h-8 w-full min-w-0 rounded border border-slate-300 bg-slate-100 px-2 text-sm text-tinte"/>
                </label>
                <button type="button" class="h-8 rounded border border-green-700 bg-green-200 px-3 text-sm font-bold text-green-900" @click="emit('sna')">{{ t('maske.sna') }}</button>
            </div>
            <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                <span>{{ t('maske.betroffener') }}<NachtragMarke v-if="nachgetragen?.has('betroffener')"/></span>
                <input v-model="eintraege.betroffener" class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
            </label>
            <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                <span>{{ t('maske.hinweise') }}<NachtragMarke v-if="nachgetragen?.has('hinweise')"/></span>
                <textarea v-model="eintraege.hinweise" rows="2" class="rounded border border-slate-400 px-2 py-1 text-sm text-tinte"/>
            </label>
        </fieldset>
    </section>
</template>
