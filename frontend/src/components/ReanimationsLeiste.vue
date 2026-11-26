<script setup lang="ts">
import {computed, nextTick, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {useTaktgeber} from '../composables/useTaktgeber'
import {dauer, useUhr} from '../composables/useUhr'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Eintraege} from '../modell/eintraege'
import {ALTERSGRUPPEN, reanimationFaellig, SCHRITTE, wartetAufKraefte, wirksameGruppe, type Altersgruppe} from '../modell/reanimation'

const props = defineProps<{graph: Abfragegraph, ruhig?: boolean, eintreffenUm?: number}>()
const eintraege = defineModel<Eintraege>({required: true})
const emit = defineEmits<{sofort: []}>()

const NEUGEBORENEN_TAKT = 120
const BEATMUNG_ALLE = 4

const {t} = useI18n()
const jetzt = useUhr()
const faellig = computed(() => reanimationFaellig(props.graph, eintraege.value.abfrage))
const reanimation = computed(() => eintraege.value.reanimation)
const gruppe = computed(() => wirksameGruppe(props.graph, eintraege.value))
const neugeboren = computed(() => gruppe.value.gruppe === 'neugeborenes')
const {schlaege, beatmung, hoerbar, freischalten} = useTaktgeber(
    () => faellig.value && reanimation.value.laeuft,
    () => neugeboren.value ? NEUGEBORENEN_TAKT : reanimation.value.takt,
    () => Boolean(props.ruhig),
    () => neugeboren.value ? BEATMUNG_ALLE : 0,
)
const ueberschrift = computed(() => {
    const name = t(`reanimation.gruppen.${gruppe.value.gruppe}`)
    return gruppe.value.alter ? t('reanimation.fuerMitAlter', {gruppe: name, alter: gruppe.value.alter}) : t('reanimation.fuer', {gruppe: name})
})
/** A component whose root element can take the focus. */
type FocusableComponent = {$el: HTMLElement}

const knopf = ref<FocusableComponent | null>(null)
const unterwegs = computed(() => wartetAufKraefte(eintraege.value, props.eintreffenUm, jetzt.value))

function setzen(aenderung: Partial<Eintraege['reanimation']>): void {
    eintraege.value.reanimation = {...reanimation.value, ...aenderung}
    emit('sofort')
}

function gruppeWaehlen(wahl: Altersgruppe): void {
    setzen({gruppe: wahl})
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
    knopf.value?.$el.focus()
}

watch(faellig, an => {
    if (props.ruhig) return
    if (an) void nextTick(fokussieren)
    else if (reanimation.value.laeuft) setzen({laeuft: false})
}, {flush: 'post'})
</script>

<template>
    <section v-if="faellig" :aria-label="t('reanimation.titel')" class="flex flex-col gap-2 rounded-lg border-2 border-error bg-error/10 p-3">
        <div class="flex flex-wrap items-center gap-3">
            <h2 class="m-0 text-base font-bold text-error">{{ t('reanimation.titel') }}</h2>
            <UButton ref="knopf" size="lg" :color="reanimation.laeuft ? 'neutral' : 'error'" :icon="reanimation.laeuft ? 'i-lucide-pause' : 'i-lucide-play'" @click="umschalten">{{ reanimation.laeuft ? t('reanimation.stopp') : t('reanimation.start') }}</UButton>
            <span v-if="reanimation.laeuft" :title="hoerbar && !ruhig ? t('reanimation.tonAn') : t('reanimation.tonAus')" :aria-label="hoerbar && !ruhig ? t('reanimation.tonAn') : t('reanimation.tonAus')" role="img">
                <UIcon :name="hoerbar && !ruhig ? 'i-lucide-volume-2' : 'i-lucide-volume-x'" aria-hidden="true"/>
            </span>
            <span v-if="reanimation.laeuft" :key="schlaege" class="schlag size-5 rounded-full bg-error" aria-hidden="true"/>
            <span v-if="reanimation.laeuft" role="status" class="font-mono text-sm">{{ t('reanimation.schlaege', {anzahl: schlaege}) }}</span>
            <b v-if="reanimation.laeuft && beatmung" class="rounded bg-info px-2 text-sm text-inverted">{{ t('reanimation.beatmen') }}</b>
            <span v-if="eintraege.zeiten.reanimation" class="font-mono text-sm text-muted">{{ t('reanimation.seit', {dauer: dauer(jetzt - eintraege.zeiten.reanimation)}) }}</span>
            <span v-if="neugeboren" class="ml-auto text-sm font-semibold">{{ t('reanimation.verhaeltnis') }}</span>
            <label v-else class="ml-auto flex items-center gap-1 text-sm">
                {{ t('reanimation.takt') }}
                <input type="number" min="100" max="120" step="1" :value="reanimation.takt" class="native-field w-16" @change="taktSetzen($event.target as HTMLInputElement)"/>
            </label>
        </div>
        <p v-if="eintraege.zeiten.reanimation" role="status" :class="['m-0 rounded px-2 py-1 text-sm font-semibold', unterwegs ? 'bg-default text-error' : 'bg-success/15 text-success']">
            <UIcon :name="unterwegs ? 'i-lucide-ambulance' : 'i-lucide-circle-check'" class="mr-1.5" aria-hidden="true"/>{{ unterwegs ? t('reanimation.unterwegs') : t('reanimation.eingetroffen') }}
        </p>
        <div class="flex flex-wrap items-center gap-2 text-sm">
            <b>{{ ueberschrift }}</b>
            <div role="group" :aria-label="t('reanimation.gruppeWaehlen')" class="ml-auto flex gap-1">
                <UButton v-for="wahl in ALTERSGRUPPEN" :key="wahl" size="sm" color="error" :variant="gruppe.gruppe === wahl ? 'solid' : 'outline'" :aria-pressed="gruppe.gruppe === wahl" @click="gruppeWaehlen(wahl)">{{ t(`reanimation.gruppen.${wahl}`) }}</UButton>
            </div>
        </div>
        <p v-if="!gruppe.sicher" role="status" class="m-0 rounded bg-warning/15 px-2 py-1 text-sm font-semibold">{{ t('reanimation.alterUnbekannt') }}</p>
        <ol class="m-0 flex flex-col gap-0.5 pl-6 text-sm">
            <li v-for="schritt in SCHRITTE[gruppe.gruppe]" :key="schritt">{{ t(`reanimation.schritte.${gruppe.gruppe}.${schritt}`) }}</li>
        </ol>
        <p v-if="gruppe.gruppe === 'saeugling' || gruppe.gruppe === 'kind'" class="m-0 text-xs">{{ t('reanimation.nurDruecken') }}</p>
        <p class="m-0 text-xs text-muted">{{ t('reanimation.entwurf') }}</p>
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
