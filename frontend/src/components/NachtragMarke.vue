<script setup lang="ts">
import {useI18n} from 'vue-i18n'

const {t} = useI18n()
</script>

<template>
    <span class="ml-1.5 rounded bg-sky-100 px-1.5 text-xs font-semibold text-akzent">{{ t('uebergabe.nachtrag') }}</span>
</template>
