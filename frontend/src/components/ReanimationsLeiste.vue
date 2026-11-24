<script setup lang="ts">
import {faCircleCheck, faPause, faPlay, faTruckMedical, faVolumeHigh, faVolumeXmark} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {useTaktgeber} from '../composables/useTaktgeber'
import {dauer, useUhr} from '../composables/useUhr'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Eintraege} from '../modell/eintraege'
import {reanimationFaellig, wartetAufKraefte} from '../modell/reanimation'

const props = defineProps<{graph: Abfragegraph, ruhig?: boolean, eintreffenUm?: number}>()
const eintraege = defineModel<Eintraege>({required: true})
const emit = defineEmits<{sofort: []}>()

const SCHRITTE = ['lage', 'frei', 'hand', 'druck', 'takt', 'weiter', 'wechsel', 'beatmung'] as const

const {t} = useI18n()
const jetzt = useUhr()
const faellig = computed(() => reanimationFaellig(props.graph, eintraege.value.abfrage))
const reanimation = computed(() => eintraege.value.reanimation)
const {schlaege, hoerbar, freischalten} = useTaktgeber(() => faellig.value && reanimation.value.laeuft, () => reanimation.value.takt, () => Boolean(props.ruhig))
const knopf = ref<HTMLButtonElement | null>(null)
const unterwegs = computed(() => wartetAufKraefte(eintraege.value, props.eintreffenUm, jetzt.value))

function setzen(aenderung: Partial<Eintraege['reanimation']>): void {
    eintraege.value.reanimation = {...reanimation.value, ...aenderung}
    emit('sofort')
}

function umschalten(): void {
    if (!reanimation.value.laeuft) freischalten()
    setzen({laeuft: !reanimation.value.laeuft})
}

function taktSetzen(feld: HTMLInputElement): void {
    const wert = Number(feld.value)
    if (feld.value.trim() && Number.isFinite(wert)) setzen({takt: Math.min(120, Math.max(100, Math.round(wert)))})
    feld.value = String(reanimation.value.takt)
}

/** Puts the focus on the start button, once the bar appears. */
function fokussieren(): void {
    knopf.value?.focus()
}

watch(faellig, an => {
    if (props.ruhig) return
    if (an) void nextTick(fokussieren)
    else if (reanimation.value.laeuft) setzen({laeuft: false})
}, {flush: 'post'})
</script>

<template>
    <section v-if="faellig" :aria-label="t('reanimation.titel')" class="flex flex-col gap-2 rounded-lg border-2 border-red-700 bg-red-50 p-3">
        <div class="flex flex-wrap items-center gap-3">
            <h2 class="m-0 text-base font-bold text-red-800">{{ t('reanimation.titel') }}</h2>
            <button ref="knopf" type="button" :class="['h-10 rounded px-4 font-semibold text-white', reanimation.laeuft ? 'bg-slate-700' : 'bg-red-700']" @click="umschalten"><FontAwesomeIcon :icon="reanimation.laeuft ? faPause : faPlay" class="mr-1.5" aria-hidden="true"/>{{ reanimation.laeuft ? t('reanimation.stopp') : t('reanimation.start') }}</button>
            <span v-if="reanimation.laeuft" :title="hoerbar && !ruhig ? t('reanimation.tonAn') : t('reanimation.tonAus')" :aria-label="hoerbar && !ruhig ? t('reanimation.tonAn') : t('reanimation.tonAus')" role="img">
                <FontAwesomeIcon :icon="hoerbar && !ruhig ? faVolumeHigh : faVolumeXmark" aria-hidden="true"/>
            </span>
            <span v-if="reanimation.laeuft" :key="schlaege" class="schlag size-5 rounded-full bg-red-600" aria-hidden="true"/>
            <span v-if="reanimation.laeuft" role="status" class="font-mono text-sm">{{ t('reanimation.schlaege', {anzahl: schlaege}) }}</span>
            <span v-if="eintraege.zeiten.reanimation" class="font-mono text-sm text-gedaempft">{{ t('reanimation.seit', {dauer: dauer(jetzt - eintraege.zeiten.reanimation)}) }}</span>
            <label class="ml-auto flex items-center gap-1 text-sm">
                {{ t('reanimation.takt') }}
                <input type="number" min="100" max="120" step="1" :value="reanimation.takt" class="h-8 w-16 rounded border border-slate-400 px-1" @change="taktSetzen($event.target as HTMLInputElement)"/>
            </label>
        </div>
        <p v-if="eintraege.zeiten.reanimation" role="status" :class="['m-0 rounded px-2 py-1 text-sm font-semibold', unterwegs ? 'bg-white text-red-900' : 'bg-green-100 text-ok']">
            <FontAwesomeIcon :icon="unterwegs ? faTruckMedical : faCircleCheck" class="mr-1.5" aria-hidden="true"/>{{ unterwegs ? t('reanimation.unterwegs') : t('reanimation.eingetroffen') }}
        </p>
        <ol class="m-0 flex flex-col gap-0.5 pl-6 text-sm">
            <li v-for="schritt in SCHRITTE" :key="schritt">{{ t(`reanimation.schritt.${schritt}`) }}</li>
        </ol>
    </section>
</template>

<style scoped>
.schlag {
    animation: schlag 0.3s ease-out;
}

@keyframes schlag {
    from { transform: scale(1.6); opacity: 1; }
    to { transform: scale(1); opacity: 0.5; }
}
</style>
