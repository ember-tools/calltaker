<script setup lang="ts">
import {faRotateRight} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {useI18n} from 'vue-i18n'
import {useNeueFassung} from '../composables/useNeueFassung'

const {t} = useI18n()
const neu = useNeueFassung()

function neuLaden(): void {
    window.location.reload()
}
</script>

<template>
    <div v-if="neu" role="status" class="flex flex-wrap items-center justify-center gap-3 bg-akzent px-4 py-2 text-sm font-semibold text-white">
        {{ t('fassung.neu') }}
        <button type="button" class="rounded bg-white px-3 py-1 text-akzent" @click="neuLaden"><FontAwesomeIcon :icon="faRotateRight" class="mr-1.5" aria-hidden="true"/>{{ t('fassung.laden') }}</button>
    </div>
</template>
