<script setup lang="ts">
import {computed, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import type {Abfragegraph} from '../modell/abfragegraph'
import type {Eintraege} from '../modell/eintraege'
import {faelligNachEintraegen} from '../phasen/anleitung'

const props = defineProps<{graph: Abfragegraph}>()
const eintraege = defineModel<Eintraege>({required: true})
const emit = defineEmits<{sofort: []}>()

const {t} = useI18n()
const faellig = computed(() => faelligNachEintraegen(props.graph, eintraege.value))
const gegeben = computed(() => new Set(eintraege.value.anleitung.gegeben))
const nichtMehrFaellig = computed(() => (props.graph.anleitungen ?? [])
    .filter(anleitung => gegeben.value.has(anleitung.id) && !faellig.value.some(f => f.id === anleitung.id)))
const wurzel = ref<HTMLElement | null>(null)

function umschalten(id: string, an: boolean): void {
    const ohne = eintraege.value.anleitung.gegeben.filter(anderes => anderes !== id)
    eintraege.value.anleitung = {gegeben: an ? [...ohne, id] : ohne}
    emit('sofort')
}

/** Puts the focus on the first instruction not given yet, or the first one. */
function fokussieren(): void {
    if (!faellig.value.length) return
    const felder = [...(wurzel.value?.querySelectorAll<HTMLInputElement>('input[type=checkbox]') ?? [])]
    ;(felder.find(feld => !feld.checked) ?? felder[0])?.focus()
}

defineExpose({fokussieren})
</script>

<template>
    <section v-if="faellig.length || nichtMehrFaellig.length" ref="wurzel" :aria-label="t('hinweise.titel')" class="flex flex-col gap-2 rounded-lg border border-default bg-default p-3">
        <h2 class="m-0 text-sm font-bold">{{ t('hinweise.titel') }}</h2>
        <article v-for="anleitung in faellig" :key="anleitung.id" :class="['rounded border p-2', gegeben.has(anleitung.id) ? 'border-success bg-success/10' : anleitung.pflicht ? 'border-warning bg-warning/10' : 'border-default bg-default']">
            <label class="flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" :checked="gegeben.has(anleitung.id)" @change="umschalten(anleitung.id, ($event.target as HTMLInputElement).checked)"/>
                {{ anleitung.titel }}
                <span v-if="anleitung.pflicht" class="rounded bg-warning/25 px-1.5 text-xs"><UIcon name="i-lucide-triangle-alert" class="mr-1" aria-hidden="true"/>{{ t('hinweise.pflicht') }}</span>
            </label>
            <ol v-if="!gegeben.has(anleitung.id)" class="m-0 mt-1 flex flex-col gap-0.5 pl-6 text-sm">
                <li v-for="satz in anleitung.saetze" :key="satz">{{ satz }}</li>
            </ol>
        </article>
        <details v-if="nichtMehrFaellig.length" class="text-sm">
            <summary class="cursor-pointer text-muted">{{ t('hinweise.nichtMehrFaellig', {anzahl: nichtMehrFaellig.length}) }}</summary>
            <label v-for="anleitung in nichtMehrFaellig" :key="anleitung.id" class="mt-1 flex items-center gap-2">
                <input type="checkbox" checked @change="umschalten(anleitung.id, ($event.target as HTMLInputElement).checked)"/>
                {{ anleitung.titel }}
            </label>
        </details>
    </section>
</template>
