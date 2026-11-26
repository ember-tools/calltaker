<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const {t} = useI18n()
</script>

<template>
    <p role="status" class="m-0 bg-warning/15 px-5 py-2 text-sm font-semibold text-warning">{{ t('verbindung.getrennt') }}</p>
</template>
