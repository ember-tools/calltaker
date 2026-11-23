<script setup lang="ts">
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useGefahrstoffe} from '../composables/useGefahrstoffe'
import {GEFAHRENZAHL, gefahrenzahlDeuten, stoffeSuchen, stoffeZu, type Stoff, type Warntafel} from '../modell/gefahrstoffe'

const tafel = defineModel<Warntafel>({required: true})
const {t} = useI18n()
const liste = useGefahrstoffe()
const name = ref('')

const stoffe = computed(() => stoffeZu(liste.value?.stoffe ?? [], tafel.value.un))
const deutung = computed(() => gefahrenzahlDeuten(tafel.value.gefahrenzahl))
const vorschlaege = computed(() => stoffeSuchen(liste.value?.stoffe ?? [], name.value))

function setzen(feld: keyof Warntafel, wert: string): void {
    tafel.value = {...tafel.value, [feld]: wert.trim().toUpperCase()}
}

function waehlen(stoff: Stoff): void {
    tafel.value = {un: stoff.un, gefahrenzahl: GEFAHRENZAHL.test(stoff.gefahrenzahl) ? stoff.gefahrenzahl : ''}
    name.value = ''
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
                <p v-if="tafel.un.length === 4 && liste && !stoffe.length" class="m-0 text-gedaempft">{{ t('warntafel.unbekannt') }}</p>
                <ul v-if="deutung.length" class="m-0 pl-5">
                    <li v-for="gefahr in deutung" :key="gefahr" :class="gefahr.includes('Wasser') ? 'font-semibold text-fehler' : ''">{{ gefahr }}</li>
                </ul>
                <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
                    {{ t('warntafel.name') }}
                    <input v-model="name" class="h-8 rounded border border-slate-400 px-2 text-sm text-tinte"/>
                </label>
                <ul v-if="vorschlaege.length" class="m-0 flex list-none flex-col gap-0.5 p-0">
                    <li v-for="stoff in vorschlaege" :key="`${stoff.un}-${stoff.klasse}-${stoff.bezeichnung}`">
                        <button type="button" class="w-full rounded border border-slate-300 px-2 py-0.5 text-left" @click="waehlen(stoff)"><span class="font-mono">{{ stoff.gefahrenzahl || '-' }} / {{ stoff.un }}</span> {{ stoff.bezeichnung }}</button>
                    </li>
                </ul>
            </div>
        </div>
    </fieldset>
</template>
