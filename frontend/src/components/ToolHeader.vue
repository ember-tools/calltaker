<script setup lang="ts">
import {AppHeader} from '@emberbox/ui'
import {useI18n} from 'vue-i18n'

/** The header of every page: the application's name, the role or page it shows, and what that page puts beside it. */
defineProps<{role?: string}>()

const {t} = useI18n()
</script>

<template>
    <AppHeader :name="t('app.name')" :subtitle="role ?? t('app.untertitel')" logo="/favicon.svg">
        <template v-if="$slots.default" #nav>
            <slot/>
        </template>
    </AppHeader>
</template>
