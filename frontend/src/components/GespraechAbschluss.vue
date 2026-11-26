<script setup lang="ts">
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{offen: string[]}>()
const emit = defineEmits<{beenden: []}>()

const {t} = useI18n()
const liste = computed(() => props.offen.map(schluessel => t(schluessel)).join(', '))
</script>

<template>
    <div class="flex flex-wrap items-center gap-3 rounded-lg border border-default bg-muted px-4 py-3">
        <span v-if="offen.length" class="text-sm text-muted">{{ t('abschluss.noch') }} <b>{{ liste }}</b></span>
        <span v-else class="text-sm font-semibold text-success">{{ t('abschluss.vollstaendig') }}</span>
        <UButton class="ml-auto" size="xl" :color="offen.length ? 'neutral' : 'primary'" :variant="offen.length ? 'subtle' : 'solid'" @click="emit('beenden')">{{ t('abschluss.beenden') }}</UButton>
    </div>
</template>
