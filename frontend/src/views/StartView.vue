<script setup lang="ts">
import {usePage, webApplicationData} from '@emberbox/ui'
import {ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useRouter} from 'vue-router'
import {anlegen, rolleVon} from '../api/uebung'
import ToolHeader from '../components/ToolHeader.vue'

const {t} = useI18n()
const router = useRouter()
const code = ref('')
const fehler = ref('')

usePage({
    title: t('start.pageTitle'),
    description: t('start.description'),
    path: '/',
    structuredData: [webApplicationData({name: t('app.name'), description: t('start.description')})],
})

/** What the start page names as the application's parts, by their catalogue keys under `start.features`. */
const FEATURES = [
    {key: 'queue', icon: 'i-lucide-phone-incoming'},
    {key: 'questioning', icon: 'i-lucide-list-checks'},
    {key: 'debrief', icon: 'i-lucide-clipboard-check'},
] as const

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
    <ToolHeader/>
    <main class="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-10 md:px-6">
        <div class="flex flex-col gap-2">
            <p class="eyebrow m-0">{{ t('start.eyebrow') }}</p>
            <h1 class="headline m-0 text-4xl">{{ t('start.title') }}</h1>
            <p class="m-0 max-w-2xl text-muted">{{ t('start.intro') }}</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
            <section class="flex flex-col gap-3 rounded-sm border border-default bg-default p-5">
                <h2 class="section-title m-0">{{ t('start.anlegenTitel') }}</h2>
                <p class="m-0 text-sm text-muted">{{ t('start.anlegenText') }}</p>
                <UButton class="mt-auto justify-center" size="lg" @click="neueUebung">{{ t('start.anlegen') }}</UButton>
            </section>
            <form class="flex flex-col gap-3 rounded-sm border border-default bg-default p-5" @submit.prevent="beitreten">
                <h2 class="section-title m-0">{{ t('start.beitretenTitel') }}</h2>
                <p class="m-0 text-sm text-muted">{{ t('start.beitretenText') }}</p>
                <UFormField :label="t('start.code')" name="code">
                    <UInput v-model="code" class="w-full" size="lg" :ui="{base: 'tabular uppercase'}" autocomplete="off" required/>
                </UFormField>
                <UButton type="submit" class="justify-center" size="lg" variant="outline">{{ t('start.beitreten') }}</UButton>
            </form>
        </div>
        <p v-if="fehler" role="alert" class="m-0 font-semibold text-error">{{ fehler }}</p>
        <ul class="m-0 grid list-none gap-4 p-0 sm:grid-cols-3">
            <li v-for="feature in FEATURES" :key="feature.key" class="flex flex-col gap-1.5">
                <UIcon :name="feature.icon" class="size-5 text-signal" aria-hidden="true"/>
                <h2 class="m-0 text-base font-semibold text-highlighted">{{ t(`start.features.${feature.key}.title`) }}</h2>
                <p class="m-0 text-sm text-muted">{{ t(`start.features.${feature.key}.text`) }}</p>
            </li>
        </ul>
        <p class="m-0 text-center text-sm"><RouterLink :to="{name: 'hilfe'}" class="font-semibold underline">{{ t('hilfe.link') }}</RouterLink></p>
    </main>
</template>
