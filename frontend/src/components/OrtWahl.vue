<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {adresslisteVerfuegbar} from '../api/adressen'
import type {Funkzelle, Kartenpunkt} from '../modell/karte'
import {ausAdresse, ausOrt, type Adressvorschlag, type Ortsangabe, type Ortsvorschlag} from '../modell/ort'
import type {Adresse} from '../modell/szenario'
import AdressSuche from './AdressSuche.vue'
import KarteLeaflet from './KarteLeaflet.vue'

const ort = defineModel<Ortsangabe>({required: true})
const text = defineModel<string>('text', {default: ''})
defineProps<{ruhig?: boolean, funkzelle?: Funkzelle}>()

const {t} = useI18n()
const listeDa = ref(true)
const gross = ref(false)

onMounted(async () => {
    listeDa.value = await adresslisteVerfuegbar()
})

const punkte = computed<Kartenpunkt[]>(() => ort.value.koordinaten
    ? [{breite: ort.value.koordinaten[0], laenge: ort.value.koordinaten[1], art: 'erfasst'}]
    : [])

const FELDER: {feld: keyof Adresse, schluessel: string, breit: boolean}[] = [
    {feld: 'strasse', schluessel: 'ort.strasse', breit: true},
    {feld: 'hausnummer', schluessel: 'ort.hausnummer', breit: false},
    {feld: 'plz', schluessel: 'ort.plz', breit: false},
    {feld: 'ortsteil', schluessel: 'ort.ortsteil', breit: true},
]

function adresse(vorschlag: Adressvorschlag): void {
    ort.value = ausAdresse(vorschlag, ort.value)
}

function platz(vorschlag: Ortsvorschlag): void {
    ort.value = ausOrt(vorschlag, ort.value)
}

function gesetzt(breite: number, laenge: number): void {
    ort.value = {...ort.value, koordinaten: [breite, laenge]}
}

function feldGeaendert(feld: keyof Adresse, wert: string): void {
    ort.value = {...ort.value, adresse: {...ort.value.adresse, [feld]: wert}}
}
</script>

<template>
    <div class="flex flex-col gap-2">
        <AdressSuche v-model="text" :beschriftung="t('ort.suche')" :ruhig="ruhig" @adresse="adresse" @ort="platz"/>
        <p v-if="!listeDa" class="m-0 text-xs text-warnung">{{ t('ort.listeFehlt') }}</p>
        <div class="grid grid-cols-6 gap-2">
            <label v-for="eintrag in FELDER" :key="eintrag.feld" :class="['flex flex-col gap-1 text-xs font-semibold text-gedaempft', eintrag.breit ? 'col-span-2' : 'col-span-1']">
                {{ t(eintrag.schluessel) }}
                <input
                    :value="ort.adresse[eintrag.feld]"
                    class="h-8 rounded border border-slate-400 bg-white px-2 text-sm font-medium text-tinte"
                    @input="feldGeaendert(eintrag.feld, ($event.target as HTMLInputElement).value)"
                />
            </label>
        </div>
        <div :class="['overflow-hidden rounded border border-rand', gross ? 'h-96' : 'h-40']">
            <KarteLeaflet :punkte="punkte" :funkzelle="funkzelle" setzbar :beschriftung="t('ort.karte')" @gesetzt="gesetzt"/>
        </div>
        <p v-if="funkzelle" class="m-0 text-xs font-semibold text-amber-800">{{ t('ort.funkzelle', {km: (funkzelle.radius / 1000).toLocaleString('de-DE', {maximumFractionDigits: 1})}) }}</p>
        <div class="flex items-center gap-2">
            <p class="m-0 flex-1 text-xs text-gedaempft">{{ t('ort.karteHinweis') }}</p>
            <button type="button" class="text-xs underline" :aria-pressed="gross" @click="gross = !gross">{{ gross ? t('ort.karteKlein') : t('ort.karteGross') }}</button>
        </div>
        <p class="m-0 text-[0.7rem] text-gedaempft">{{ t('ort.quelle') }}</p>
    </div>
</template>
