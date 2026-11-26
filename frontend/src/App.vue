<script setup lang="ts">
import {AppFooter, EmberboxApp} from '@emberbox/ui'
import {useHead} from '@unhead/vue'
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {useRoute} from 'vue-router'

const {t} = useI18n()
const route = useRoute()

/** Start and help are prerendered and set their own title; every exercise page stays out of search engines. */
const isPublic = computed(() => route.meta.public === true)

useHead({
    title: () => (isPublic.value ? undefined : t('app.name')),
    meta: () => (isPublic.value ? [] : [{name: 'robots', content: 'noindex, nofollow'}]),
})
</script>

<template>
    <EmberboxApp>
        <div class="flex min-h-screen flex-col">
            <RouterView :key="$route.fullPath"/>
            <AppFooter :tool="t('app.name')" source="https://github.com/ember-tools/calltaker" license="AGPL-3.0-or-later" help="/hilfe" :notice="t('fuss.hinweis')"/>
        </div>
    </EmberboxApp>
</template>
