<script setup lang="ts">
import {faTriangleExclamation} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useGefahrstoffe} from '../composables/useGefahrstoffe'
import {GEFAHRENZAHL, gefahrenzahlDeuten, gefahrenzahlenZu, stoffeSuchen, stoffeZu, type Stoff, type Warntafel} from '../modell/gefahrstoffe'

const tafel = defineModel<Warntafel>({required: true})
const {t} = useI18n()
const liste = useGefahrstoffe()
const name = ref('')

const stoffe = computed(() => stoffeZu(liste.value?.stoffe ?? [], tafel.value.un))
const deutung = computed(() => gefahrenzahlDeuten(tafel.value.gefahrenzahl))
const vorschlaege = computed(() => stoffeSuchen(liste.value?.stoffe ?? [], name.value))
const moeglicheZahlen = computed(() => gefahrenzahlenZu(liste.value?.stoffe ?? [], tafel.value.un))
const ergaenzt = ref('')

/**
 * Takes a typed value. A complete UN number fills in its hazard number when the list gives only
 * one and the trainee has not typed another; a filled-in one is replaced when the number changes.
 *
 * @param feld the field
 * @param wert what was typed
 */
function setzen(feld: keyof Warntafel, wert: string): void {
    const neu = {...tafel.value, [feld]: wert.trim().toUpperCase()}
    if (feld === 'un') {
        const zahlen = gefahrenzahlenZu(liste.value?.stoffe ?? [], neu.un)
        const selbstGetippt = neu.gefahrenzahl && neu.gefahrenzahl !== ergaenzt.value
        if (!selbstGetippt) {
            ergaenzt.value = zahlen.length === 1 ? zahlen[0]! : ''
            neu.gefahrenzahl = ergaenzt.value
        }
    } else {
        ergaenzt.value = ''
    }
    tafel.value = neu
}

function zahlWaehlen(zahl: string): void {
    ergaenzt.value = zahl
    tafel.value = {...tafel.value, gefahrenzahl: zahl}
}

const markiert = ref(0)
const geschlossen = ref(false)
const offen = computed(() => !geschlossen.value && vorschlaege.value.length > 0)

function waehlen(stoff: Stoff): void {
    tafel.value = {un: stoff.un, gefahrenzahl: GEFAHRENZAHL.test(stoff.gefahrenzahl) ? stoff.gefahrenzahl : ''}
    ergaenzt.value = tafel.value.gefahrenzahl
    name.value = ''
}

/**
 * Moves through the suggestions with the arrow keys, takes one with Enter and closes them with
 * Escape; Enter on an open list never submits the surrounding question.
 *
 * @param ereignis the key pressed
 */
function taste(ereignis: KeyboardEvent): void {
    if (!offen.value) return
    const anzahl = vorschlaege.value.length
    if (ereignis.key === 'ArrowDown') markiert.value = (markiert.value + 1) % anzahl
    else if (ereignis.key === 'ArrowUp') markiert.value = (markiert.value - 1 + anzahl) % anzahl
    else if (ereignis.key === 'Enter') waehlen(vorschlaege.value[markiert.value]!)
    else if (ereignis.key === 'Escape') geschlossen.value = true
    else return
    ereignis.preventDefault()
}
</script>

<template>
    <fieldset class="m-0 flex min-w-0 flex-col gap-1.5 border-0 p-0">
        <legend class="mb-1 font-bold">{{ t('warntafel.titel') }}</legend>
        <div class="flex flex-wrap items-start gap-3">
            <div class="flex w-28 flex-col overflow-hidden rounded border-2 border-black bg-orange-500">
                <input :value="tafel.gefahrenzahl" :aria-label="t('warntafel.gefahrenzahl')" maxlength="4" class="h-9 border-0 border-b-2 border-black bg-transparent text-center font-mono text-lg font-bold text-black" @input="setzen('gefahrenzahl', ($event.target as HTMLInputElement).value)"/>
                <input :value="tafel.un" :aria-label="t('warntafel.un')" maxlength="4" inputmode="numeric" class="h-9 border-0 bg-transparent text-center font-mono text-lg font-bold text-black" @input="setzen('un', ($event.target as HTMLInputElement).value)"/>
            </div>
            <div class="flex min-w-0 flex-1 flex-col gap-1 text-sm">
                <p v-for="stoff in stoffe" :key="`${stoff.klasse}-${stoff.bezeichnung}`" class="m-0"><b>{{ stoff.bezeichnung }}</b> · {{ t('warntafel.klasse', {klasse: stoff.klasse}) }}</p>
                <p v-if="moeglicheZahlen.length > 1 && !tafel.gefahrenzahl" class="m-0 flex flex-wrap items-center gap-1.5">
                    {{ t('warntafel.mehrere') }}
                    <button v-for="zahl in moeglicheZahlen" :key="zahl" type="button" class="rounded border border-slate-400 px-2 font-mono" @click="zahlWaehlen(zahl)">{{ zahl }}</button>
                </p>
                <p v-if="tafel.un.length === 4 && liste && !stoffe.length" class="m-0 text-gedaempft">{{ t('warntafel.unbekannt') }}</p>
                <ul v-if="deutung.length" class="m-0 pl-5">
                    <li v-for="gefahr in deutung" :key="gefahr" :class="gefahr.includes('Wasser') ? 'font-semibold text-fehler' : ''"><FontAwesomeIcon v-if="gefahr.includes('Wasser')" :icon="faTriangleExclamation" class="mr-1" aria-hidden="true"/>{{ gefahr }}</li>
                </ul>
                <label class="relative flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('warntafel.name') }}
                    <input
                        v-model="name" role="combobox" autocomplete="off" aria-autocomplete="list" aria-controls="warntafel-stoffe"
                        :aria-expanded="offen" :aria-activedescendant="offen && markiert >= 0 ? `warntafel-stoff-${markiert}` : undefined"
                        class="h-8 rounded border border-slate-400 px-2 text-sm font-normal text-tinte"
                        @input="markiert = 0; geschlossen = false" @keydown="taste" @blur="geschlossen = true"
                    />
                    <ul v-if="offen" id="warntafel-stoffe" role="listbox" class="absolute top-full right-0 left-0 z-20 m-0 mt-1 max-h-64 list-none overflow-y-auto rounded border border-slate-300 bg-white p-0 text-sm font-normal text-tinte shadow-lg">
                        <li
                            v-for="(stoff, stelle) in vorschlaege" :id="`warntafel-stoff-${stelle}`" :key="`${stoff.un}-${stoff.klasse}-${stoff.bezeichnung}`"
                            role="option" tabindex="-1" :aria-selected="stelle === markiert" :class="['cursor-pointer px-2 py-1', stelle === markiert ? 'bg-sky-100' : '']"
                            @mousedown.prevent="waehlen(stoff)"
                        ><span class="font-mono">{{ stoff.gefahrenzahl || '-' }} / {{ stoff.un }}</span> {{ stoff.bezeichnung }}</li>
                    </ul>
                </label>
            </div>
        </div>
    </fieldset>
</template>
