<script setup lang="ts">
import {computed, ref, toRef, useId} from 'vue'
import {useI18n} from 'vue-i18n'
import {useAdresssuche} from '../composables/useAdresssuche'
import type {Adressvorschlag, Ortsvorschlag} from '../modell/ort'

/** One entry of the suggestion list: an address from the list, or a named place. */
type Eintrag = {art: 'adresse', vorschlag: Adressvorschlag} | {art: 'ort', vorschlag: Ortsvorschlag}

const props = defineProps<{beschriftung: string, ruhig?: boolean}>()
const text = defineModel<string>({default: ''})
const emit = defineEmits<{adresse: [vorschlag: Adressvorschlag], ort: [vorschlag: Ortsvorschlag]}>()

const {t} = useI18n()
const kennung = useId()
const {adressen, orte, uebernommen} = useAdresssuche(toRef(text), () => props.ruhig)
const markiert = ref(-1)
const offen = ref(false)

/**
 * The suggestions in the order they are offered: doors that match exactly, then named places,
 * since emergencies happen at stations and shops more often than at a street at large, then
 * streets that match exactly, then streets only spelled or sounding almost like the text.
 */
const eintraege = computed<Eintrag[]>(() => {
    const adresse = (vorschlag: Adressvorschlag): Eintrag => ({art: 'adresse', vorschlag})
    const genau = adressen.value.filter(vorschlag => !vorschlag.ungefaehr)
    return [
        ...genau.filter(vorschlag => vorschlag.hausnummer).map(adresse),
        ...orte.value.map(vorschlag => ({art: 'ort' as const, vorschlag})),
        ...genau.filter(vorschlag => !vorschlag.hausnummer).map(adresse),
        ...adressen.value.filter(vorschlag => vorschlag.ungefaehr).map(adresse),
    ]
})

function waehlen(eintrag: Eintrag): void {
    offen.value = false
    markiert.value = -1
    if (eintrag.art === 'adresse') {
        const tuer = Boolean(eintrag.vorschlag.hausnummer)
        const neu = tuer ? eintrag.vorschlag.beschriftung : `${eintrag.vorschlag.strasse} `
        if (tuer) uebernommen(neu)
        text.value = neu
        emit('adresse', eintrag.vorschlag)
    } else {
        uebernommen(eintrag.vorschlag.beschriftung)
        text.value = eintrag.vorschlag.beschriftung
        emit('ort', eintrag.vorschlag)
    }
}

function taste(ereignis: KeyboardEvent): void {
    const anzahl = eintraege.value.length
    if (ereignis.key === 'ArrowDown' && anzahl) {
        offen.value = true
        markiert.value = (markiert.value + 1) % anzahl
    } else if (ereignis.key === 'ArrowUp' && anzahl) {
        markiert.value = (markiert.value - 1 + anzahl) % anzahl
    } else if (ereignis.key === 'Enter' && offen.value && eintraege.value[markiert.value]) {
        waehlen(eintraege.value[markiert.value]!)
    } else if (ereignis.key === 'Escape') {
        offen.value = false
        return
    } else {
        return
    }
    ereignis.preventDefault()
}

const zeigen = computed(() => offen.value && eintraege.value.length > 0)
</script>

<template>
    <div class="relative">
        <label class="flex flex-col gap-1 text-xs font-semibold text-gedaempft">
            {{ props.beschriftung }}
            <input
                v-model="text"
                role="combobox"
                :aria-expanded="zeigen"
                :aria-controls="`${kennung}-liste`"
                :aria-activedescendant="markiert >= 0 ? `${kennung}-${markiert}` : undefined"
                autocomplete="off"
                class="h-8 rounded border border-slate-400 bg-white px-2 text-sm font-medium text-tinte"
                @input="offen = true; markiert = -1"
                @keydown="taste"
                @blur="offen = false"
            />
        </label>
        <ul v-show="zeigen" :id="`${kennung}-liste`" role="listbox" class="absolute z-[1000] m-0 mt-1 w-full list-none rounded border border-rand bg-white p-0 text-sm shadow-lg">
            <li
                v-for="(eintrag, stelle) in eintraege"
                :id="`${kennung}-${stelle}`"
                :key="`${stelle}-${eintrag.art}-${eintrag.vorschlag.beschriftung}`"
                role="option"
                tabindex="-1"
                :aria-selected="stelle === markiert"
                :class="['cursor-pointer px-2 py-1.5', stelle === markiert ? 'bg-sky-100' : '', stelle > 0 && eintrag.art !== eintraege[stelle - 1]?.art ? 'border-t border-rand' : '']"
                @mousedown.prevent="waehlen(eintrag)"
            >
                <span v-if="eintrag.art === 'ort'" class="mr-1 text-xs font-semibold text-gedaempft">{{ t('ort.ort') }}</span>
                <span v-else-if="eintrag.vorschlag.ungefaehr" class="mr-1 text-xs font-semibold text-warnung">{{ t('ort.aehnlich') }}</span>{{ eintrag.vorschlag.beschriftung }}
            </li>
            <li v-if="orte.length" role="presentation" class="px-2 py-1 text-xs text-gedaempft">{{ t('ort.orteQuelle') }}</li>
        </ul>
    </div>
</template>
