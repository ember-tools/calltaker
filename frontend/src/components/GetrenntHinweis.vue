<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const {t} = useI18n()
</script>

<template>
    <p role="status" class="m-0 bg-amber-100 px-5 py-2 text-sm font-semibold text-amber-900">{{ t('verbindung.getrennt') }}</p>
</template>
