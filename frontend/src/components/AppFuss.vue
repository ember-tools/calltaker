<script setup lang="ts">
import {faGithub} from '@fortawesome/free-brands-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {useI18n} from 'vue-i18n'

const QUELLE = 'https://github.com/rainbowdashlabs/calltaker'
const commit = __COMMIT__
const {t} = useI18n()

/** The build time from the bundle, shown in the reader's time zone. */
function gebaut(): string {
    const zeitpunkt = new Date(__GEBAUT__)
    return Number.isNaN(zeitpunkt.getTime()) ? '' : zeitpunkt.toLocaleString('de-DE', {dateStyle: 'medium', timeStyle: 'short'})
}
</script>

<template>
    <footer class="mt-auto border-t border-rand">
        <div class="mx-auto flex w-full max-w-[1560px] flex-col items-center gap-1 px-4 py-5 text-center text-[13px] text-gedaempft md:px-6">
            <a :href="QUELLE" target="_blank" rel="noreferrer noopener" class="flex items-center gap-2 text-tinte hover:underline">
                <FontAwesomeIcon :icon="faGithub" aria-hidden="true"/>
                {{ t('fuss.quelle') }}
            </a>
            <span>{{ t('fuss.urheber') }}</span>
            <span>{{ t('fuss.gemacht') }}</span>
            <span>{{ t('fuss.lizenz') }}</span>
            <span class="tabular-nums">{{ t('fuss.fassung', {commit, gebaut: gebaut()}) }}</span>
        </div>
    </footer>
</template>
