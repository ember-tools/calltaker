<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {gespraechsdauer, useUhr, wartezeit} from '../composables/useUhr'
import {useKlingelton} from '../composables/useKlingelton'
import {anzeigen} from '../modell/rufnummer'
import type {AnrufSicht, TraineeZustand} from '../modell/uebung'

/**
 * The queue of waiting calls. It rings while a call waits, nobody is on the phone and the exercise
 * runs; with `quiet`, as in the help page's example, it never makes a sound.
 */
const props = defineProps<{zustand: TraineeZustand, quiet?: boolean}>()
const emit = defineEmits<{bereit: [], annehmen: [anrufId: string]}>()

const {t} = useI18n()
const jetzt = useUhr()
const wartend = computed(() => props.zustand.anrufe.filter(anruf => anruf.zustand === 'wartet'))
const gespraech = computed(() => props.zustand.anrufe.find(anruf => anruf.zustand === 'gespraech'))
const klingelt = computed(() => !props.quiet && wartend.value.length > 0 && !gespraech.value && !props.zustand.engine.pausiert)
const klingelton = useKlingelton(klingelt)

function nummer(anruf: AnrufSicht): string {
    return anruf.rufnummer ? anzeigen(anruf.rufnummer) : t('warteschlange.unterdrueckt')
}
</script>

<template>
    <div class="flex flex-wrap items-center gap-3">
        <UButton v-if="!zustand.engine.gestartet" color="success" @click="emit('bereit')">{{ t('warteschlange.bereit') }}</UButton>
        <span v-if="!zustand.engine.gestartet" class="text-sm text-muted">{{ t('warteschlange.bereitText') }}</span>
        <span class="text-xs font-semibold tracking-wider text-muted">{{ t('warteschlange.titel') }}</span>
        <span v-if="wartend.length === 0" class="text-sm text-dimmed">{{ t('warteschlange.leer') }}</span>
        <div v-for="(anruf, stelle) in wartend" :key="anruf.id" :class="['flex items-center gap-2.5 rounded-md border px-3 py-1', stelle === 0 ? 'border-warning/60 bg-warning/15' : 'border-default bg-elevated']">
            <UIcon :name="anruf.rufnummer ? 'i-lucide-phone-incoming' : 'i-lucide-eye-off'" class="text-warning" aria-hidden="true"/>
            <span class="font-mono text-sm">{{ nummer(anruf) }}</span>
            <span class="font-mono text-sm text-warning">{{ wartezeit(anruf.klingeltSeit, jetzt, zustand.engine.pausiertSeit) }}</span>
            <UButton v-if="stelle === 0 && !gespraech" size="xs" color="warning" icon="i-lucide-phone" @click="emit('annehmen', anruf.id)">{{ t('warteschlange.annehmen') }}</UButton>
        </div>
        <span v-if="zustand.engine.pausiert" class="rounded bg-accented px-2 py-0.5 text-xs font-semibold"><UIcon name="i-lucide-pause" class="mr-1" aria-hidden="true"/>{{ t(zustand.engine.automatischPausiert ? 'warteschlange.automatisch' : 'warteschlange.pausiert') }}</span>
        <label class="ml-auto flex items-center gap-1.5 text-xs text-muted">
            <input v-model="klingelton" type="checkbox"/>
            <UIcon name="i-lucide-bell" aria-hidden="true"/>
            {{ t('warteschlange.klingelton') }}
        </label>
        <div v-if="gespraech" class="flex items-center gap-2.5 rounded-md border border-success/60 bg-success/15 px-3 py-1">
            <UIcon name="i-lucide-headset" class="text-success" aria-hidden="true"/>
            <span class="text-xs font-bold text-success">{{ t('warteschlange.imGespraech') }}</span>
            <span class="font-mono">{{ nummer(gespraech) }}</span>
            <span class="font-mono text-success">{{ gespraechsdauer(gespraech.angenommenUm, jetzt) }}</span>
        </div>
    </div>
</template>
