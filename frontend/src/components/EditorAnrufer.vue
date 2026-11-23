<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import type {Entwurf} from '../modell/szenarioentwurf'
import {BESCHRIFTUNG, FELD} from './formular'

const entwurf = defineModel<Entwurf>({required: true})

const {t} = useI18n()
const STIMMUNGEN = ['ruhig', 'aufgeregt', 'panisch', 'verwirrt'] as const

function unterdruecken(an: boolean): void {
    entwurf.value.anrufer = {...entwurf.value.anrufer, rufnummerUnterdrueckt: an, rufnummer: an ? '' : entwurf.value.anrufer.rufnummer}
}
</script>

<template>
    <fieldset class="m-0 grid grid-cols-2 gap-2 rounded border border-rand p-3">
        <legend class="px-1 text-sm font-bold">{{ t('editor.anrufer') }}</legend>
        <label :class="BESCHRIFTUNG">{{ t('maske.name') }}<input v-model="entwurf.anrufer.name" :class="FELD"/></label>
        <label :class="BESCHRIFTUNG">{{ t('editor.betroffener') }}<input v-model="entwurf.betroffener!.name" :class="FELD"/></label>
        <label class="col-span-2 flex items-center gap-2 text-sm"><input :checked="entwurf.anrufer.rufnummerUnterdrueckt" type="checkbox" @change="unterdruecken(($event.target as HTMLInputElement).checked)"/>{{ t('editor.unterdrueckt') }}</label>
        <label v-if="!entwurf.anrufer.rufnummerUnterdrueckt" :class="BESCHRIFTUNG">{{ t('editor.rufnummer') }}<input v-model="entwurf.anrufer.rufnummer" type="tel" :class="FELD"/></label>
        <label :class="BESCHRIFTUNG">{{ t('editor.rueckrufnummer') }}<input v-model="entwurf.anrufer.rueckrufnummer" type="tel" :placeholder="entwurf.anrufer.rufnummerUnterdrueckt ? '' : t('editor.wieAngezeigt')" :class="FELD"/></label>
    </fieldset>
    <fieldset class="m-0 grid grid-cols-2 gap-2 rounded border border-rand p-3">
        <legend class="px-1 text-sm font-bold">{{ t('editor.rolle') }}</legend>
        <label :class="BESCHRIFTUNG">{{ t('editor.stimmung') }}
            <select v-model="entwurf.rolle.stimmung" :class="FELD">
                <option :value="undefined">{{ t('editor.keineStimmung') }}</option>
                <option v-for="stimmung in STIMMUNGEN" :key="stimmung" :value="stimmung">{{ t(`editor.stimmungen.${stimmung}`) }}</option>
            </select>
        </label>
        <label :class="BESCHRIFTUNG">{{ t('editor.sprache') }}<input v-model="entwurf.rolle.sprache" :class="FELD"/></label>
        <label :class="['col-span-2', BESCHRIFTUNG]">{{ t('editor.notizen') }}<textarea v-model="entwurf.rolle.notizen" rows="3" class="rounded border border-slate-400 bg-white px-2 py-1 text-sm font-medium text-tinte" /></label>
    </fieldset>
</template>
