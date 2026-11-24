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
        <div class="mx-auto grid w-full max-w-[1560px] gap-4 px-4 py-5 text-[13px] text-gedaempft md:grid-cols-[1fr_auto_1fr] md:px-6">
            <p class="m-0 max-w-sm text-center md:text-left">{{ t('fuss.hinweis') }}</p>
            <div class="flex flex-col items-center gap-1 text-center">
                <p class="m-0 flex items-center gap-3">
                    <a :href="QUELLE" target="_blank" rel="noreferrer noopener" class="flex items-center gap-2 text-tinte hover:underline">
                        <FontAwesomeIcon :icon="faGithub" aria-hidden="true"/>
                        {{ t('fuss.quelle') }}
                    </a>
                    <span aria-hidden="true">·</span>
                    <RouterLink :to="{name: 'hilfe'}" class="text-tinte hover:underline">{{ t('hilfe.fuss') }}</RouterLink>
                </p>
                <span>{{ t('fuss.urheber') }}</span>
                <span>{{ t('fuss.gemacht') }}</span>
                <span>{{ t('fuss.lizenz') }}</span>
                <span class="tabular-nums">{{ t('fuss.fassung', {commit, gebaut: gebaut()}) }}</span>
            </div>
        </div>
    </footer>
</template>
