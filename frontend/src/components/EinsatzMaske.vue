<script setup lang="ts">
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
import WarntafelAnzeige from './WarntafelAnzeige.vue'

const props = defineProps<{anruf: AnrufSicht, stichwort?: string, alter?: string, ruhig?: boolean, warntafel?: Warntafel, nachgetragen?: Set<Nachtrag>}>()
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
    <section ref="wurzel" :aria-label="t('maske.titel')" class="flex flex-col gap-3 rounded-lg border border-default bg-default p-3.5">
        <h2 class="section-title m-0">{{ t('maske.titel') }}</h2>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.mitteiler') }}<NachtragMarke v-if="nachgetragen?.has('anrufer')"/></legend>
            <div class="grid grid-cols-2 gap-2">
                <label class="flex flex-col gap-1 field-label">
                    {{ t('maske.name') }}
                    <input v-model="eintraege.anrufer.name" class="native-field"/>
                </label>
                <label class="flex flex-col gap-1 field-label">
                    {{ t('maske.telefon') }}
                    <input :value="anruf.rufnummer ? anzeigen(anruf.rufnummer) : t('warteschlange.unterdrueckt')" readonly class="native-field w-full min-w-0 bg-elevated font-mono"/>
                </label>
            </div>
            <div v-if="!anruf.rufnummerUnterdrueckt" class="flex flex-wrap gap-2">
                <UButton size="sm" variant="soft" :color="eintraege.anrufer.rufnummerBestaetigt ? 'success' : 'info'" @click="bestaetigen">
                    <UIcon v-if="eintraege.anrufer.rufnummerBestaetigt" name="i-lucide-check" class="mr-1" aria-hidden="true"/>
                    {{ eintraege.anrufer.rufnummerBestaetigt ? t('maske.bestaetigt') : t('maske.bestaetigen') }}
                </UButton>
                <UButton color="neutral" variant="outline" size="sm" @click="andere">{{ t('maske.andere') }}</UButton>
            </div>
            <label v-if="andereNummer" class="flex flex-col gap-1 field-label">
                {{ t('maske.rueckruf') }}
                <input v-model="eintraege.anrufer.rueckrufnummer" inputmode="tel" class="native-field font-mono"/>
            </label>
        </fieldset>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.einsatzort') }}<NachtragMarke v-if="nachgetragen?.has('ort')"/></legend>
            <OrtWahl v-model="ort" v-model:text="suche" :ruhig="ruhig" :funkzelle="anruf.funkzelle"/>
            <label class="flex flex-col gap-1 field-label">
                {{ t('maske.objekt') }}
                <input v-model="eintraege.ort.objekt" class="native-field"/>
            </label>
            <div class="grid grid-cols-2 gap-2">
                <label v-for="feld in ORTSFELDER" :key="feld" class="flex flex-col gap-1 field-label">
                    {{ t(`maske.${feld}`) }}
                    <input v-model="eintraege.ort[feld]" class="native-field"/>
                </label>
            </div>
        </fieldset>
        <p v-if="warntafel" class="m-0 flex flex-wrap items-center gap-2 text-sm"><span class="text-xs font-semibold text-muted">{{ t('warntafel.titel') }}</span><WarntafelAnzeige :tafel="warntafel"/></p>
        <fieldset class="m-0 min-w-0 flex flex-col gap-1.5 border-0 p-0">
            <legend class="mb-1 font-bold">{{ t('maske.ereignis') }}</legend>
            <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto] items-end gap-2">
                <label class="flex flex-col gap-1 field-label">
                    <span>{{ t('maske.stichwort') }}<NachtragMarke v-if="nachgetragen?.has('code')"/></span>
                    <input :value="stichwort ?? ''" readonly class="native-field w-full min-w-0 bg-elevated font-mono"/>
                </label>
                <label class="flex flex-col gap-1 field-label">
                    {{ t('maske.alter') }}
                    <input :value="alter ?? ''" readonly class="native-field w-full min-w-0 bg-elevated"/>
                </label>
                <UButton size="sm" color="success" variant="subtle" @click="emit('sna')">{{ t('maske.sna') }}</UButton>
            </div>
            <label class="flex flex-col gap-1 field-label">
                <span>{{ t('maske.betroffener') }}<NachtragMarke v-if="nachgetragen?.has('betroffener')"/></span>
                <input v-model="eintraege.betroffener" class="native-field"/>
            </label>
            <label class="flex flex-col gap-1 field-label">
                <span>{{ t('maske.hinweise') }}<NachtragMarke v-if="nachgetragen?.has('hinweise')"/></span>
                <textarea v-model="eintraege.hinweise" rows="2" class="native-field"/>
            </label>
        </fieldset>
    </section>
</template>
