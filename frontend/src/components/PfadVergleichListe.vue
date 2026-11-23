<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import type {Pfadvergleich, Schrittstand} from '../modell/wahrheitspfad'

defineProps<{vergleich: Pfadvergleich, live?: boolean}>()

const {t} = useI18n()
const SCHRITT: Record<Schrittstand, string> = {gleich: 'text-ok', anders: 'bg-red-50 text-fehler', offen: 'text-gedaempft', hier: 'bg-amber-100 font-bold'}
</script>

<template>
    <div class="flex flex-col gap-2">
        <ol class="m-0 flex list-none flex-col gap-0.5 p-0" :aria-label="t('wahrheit.pfad')">
            <li v-for="schritt in vergleich.schritte" :key="schritt.knoten" :class="['rounded px-1.5 py-0.5', SCHRITT[schritt.stand]]" :aria-current="live && schritt.stand === 'hier' ? 'step' : undefined">
                <span class="text-gedaempft">{{ schritt.frage }}</span> · <b>{{ schritt.soll || t('editor.leer') }}</b>
                <span v-if="schritt.stand === 'anders'"> · {{ t('wahrheit.trainee', {ist: schritt.ist}) }}</span>
                <span v-if="vergleich.abzweigung?.knoten === schritt.knoten" class="ml-1 text-xs font-bold uppercase">{{ t('wahrheit.abzweigung') }}</span>
            </li>
        </ol>
        <p v-if="vergleich.abzweigung && !vergleich.schritte.some(s => s.knoten === vergleich.abzweigung!.knoten)" class="m-0 rounded bg-red-50 p-2 text-fehler">{{ t('wahrheit.abzweigungAbseits', {frage: vergleich.abzweigung.frage, ist: vergleich.abzweigung.ist}) }}</p>
        <p v-if="live && vergleich.abseits" class="m-0 rounded bg-amber-100 p-2" role="status">
            {{ t('wahrheit.abseits', {frage: vergleich.abseits.frage}) }}
            <b>{{ vergleich.abseits.soll ?? t('wahrheit.improvisieren') }}</b>
        </p>
    </div>
</template>
