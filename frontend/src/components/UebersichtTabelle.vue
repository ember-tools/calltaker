<script setup lang="ts">
import {useI18n} from 'vue-i18n'
import {dauer} from '../composables/useUhr'
import type {Rolle} from '../modell/uebung'
import type {Bewertung, Urteil} from '../phasen/typen'
import type {Uebersichtszeile} from '../phasen/uebersicht'

defineProps<{zeilen: Uebersichtszeile[], code: string, rolle: Rolle}>()

const {t} = useI18n()
const FARBE: Record<Urteil, string> = {richtig: 'text-ok', teilweise: 'text-warnung', falsch: 'text-fehler', offen: 'text-fehler', hinweis: ''}

/**
 * A comparison as a short mark for the table.
 *
 * @param bewertung the comparison, if the call has one for this field
 * @returns the mark
 */
function marke(bewertung?: Bewertung): string {
    if (!bewertung) return ''
    if (bewertung.abstand !== undefined) return `${bewertung.abstand} m`
    if (bewertung.stufe) return t(`stufe.${bewertung.stufe}`)
    return t(`debrief.urteil.${bewertung.urteil}`)
}

/**
 * A time for the table.
 *
 * @param sekunden the seconds, if reached
 * @returns "m:ss" or an empty text
 */
function zeit(sekunden?: number): string {
    return sekunden === undefined ? '' : dauer(sekunden)
}
</script>

<template>
    <p v-if="zeilen.length === 0" class="m-0 text-sm text-gedaempft">{{ t('auswertung.keine') }}</p>
    <table v-else class="w-full border-collapse text-sm">
        <thead>
            <tr class="text-left text-xs text-gedaempft">
                <th class="py-1 pr-2">{{ t('auswertung.anruf') }}</th>
                <th class="py-1 pr-2">{{ t('bewertung.code') }}</th>
                <th class="py-1 pr-2">{{ t('bewertung.adresse') }}</th>
                <th class="py-1 pr-2">{{ t('bewertung.punkt') }}</th>
                <th class="py-1 pr-2">{{ t('bewertung.rueckrufnummer') }}</th>
                <th class="py-1 pr-2">{{ t('debrief.zeit.code') }}</th>
                <th class="py-1">{{ t('debrief.zeit.gespraech') }}</th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="zeile in zeilen" :key="zeile.id" class="border-t border-rand">
                <th scope="row" class="py-1 pr-2 text-left font-normal">
                    <RouterLink :to="{name: `${rolle}-debrief`, params: {code, anrufId: zeile.id}}" class="underline">{{ zeile.titel }}</RouterLink>
                </th>
                <td v-for="(bewertung, spalte) in [zeile.code, zeile.adresse, zeile.punkt, zeile.rueckrufnummer]" :key="spalte" :class="['py-1 pr-2', bewertung ? FARBE[bewertung.urteil] : '']">{{ marke(bewertung) }}</td>
                <td class="py-1 pr-2 font-mono">{{ zeit(zeile.zeiten.code) }}</td>
                <td class="py-1 font-mono">{{ zeit(zeile.zeiten.gespraech) }}</td>
            </tr>
        </tbody>
    </table>
</template>
