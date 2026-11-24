<script setup lang="ts">
import {ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useRouter} from 'vue-router'
import {anlegen, rolleVon} from '../api/uebung'

const {t} = useI18n()
const router = useRouter()
const code = ref('')
const fehler = ref('')

async function neueUebung(): Promise<void> {
    fehler.value = ''
    try {
        const codes = await anlegen()
        await router.push({name: 'ausbilder', params: {code: codes.ausbilderCode}})
    } catch (e) {
        fehler.value = (e as Error).message
    }
}

async function beitreten(): Promise<void> {
    fehler.value = ''
    const eingabe = code.value.trim().toUpperCase()
    try {
        const rolle = await rolleVon(eingabe)
        await router.push({name: rolle, params: {code: eingabe}})
    } catch (e) {
        fehler.value = (e as Error).message
    }
}
</script>

<template>
    <main class="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 p-6">
        <div>
            <h1 class="m-0 font-condensed text-4xl font-bold tracking-wide">{{ t('app.name') }}</h1>
            <p class="m-0 text-gedaempft">{{ t('app.untertitel') }}</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
            <section class="flex flex-col gap-3 rounded-lg border border-rand bg-flaeche p-5">
                <h2 class="m-0 text-lg font-bold">{{ t('start.anlegenTitel') }}</h2>
                <p class="m-0 text-sm text-gedaempft">{{ t('start.anlegenText') }}</p>
                <button type="button" class="mt-auto h-11 rounded-md bg-akzent font-semibold text-white" @click="neueUebung">{{ t('start.anlegen') }}</button>
            </section>
            <form class="flex flex-col gap-3 rounded-lg border border-rand bg-flaeche p-5" @submit.prevent="beitreten">
                <h2 class="m-0 text-lg font-bold">{{ t('start.beitretenTitel') }}</h2>
                <p class="m-0 text-sm text-gedaempft">{{ t('start.beitretenText') }}</p>
                <label class="flex flex-col gap-1 text-sm font-semibold">
                    {{ t('start.code') }}
                    <input v-model="code" class="h-11 rounded-md border border-slate-400 px-3 font-mono uppercase" autocomplete="off" required/>
                </label>
                <button type="submit" class="h-11 rounded-md border border-akzent font-semibold text-akzent">{{ t('start.beitreten') }}</button>
            </form>
        </div>
        <p v-if="fehler" role="alert" class="m-0 font-semibold text-fehler">{{ fehler }}</p>
        <p class="m-0 text-center text-sm"><RouterLink :to="{name: 'hilfe'}" class="font-semibold text-akzent underline">{{ t('hilfe.link') }}</RouterLink></p>
    </main>
</template>
