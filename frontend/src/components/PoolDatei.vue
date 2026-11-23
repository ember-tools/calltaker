<script setup lang="ts">
import {ref} from 'vue'
import {useI18n} from 'vue-i18n'

const props = defineProps<{
    code: string
    absicht: (art: string, daten: Record<string, unknown>) => Promise<Record<string, unknown>>
}>()
const emit = defineEmits<{exportiert: []}>()

const {t} = useI18n()
const modus = ref<'anhaengen' | 'ersetzen'>('anhaengen')
const meldung = ref('')
const fehler = ref(false)

async function hochladen(ereignis: Event): Promise<void> {
    const feld = ereignis.target as HTMLInputElement
    const datei = feld.files?.[0]
    feld.value = ''
    if (!datei) return
    let inhalt: unknown
    try {
        inhalt = JSON.parse(await datei.text())
    } catch {
        zeige(t('ausbilder.keinJson'), true)
        return
    }
    try {
        const ergebnis = await props.absicht('pool.importieren', {datei: inhalt, modus: modus.value})
        zeige(zusammenfassung(ergebnis.befunde as Record<string, unknown[]>), false)
    } catch (e) {
        zeige((e as Error).message, true)
    }
}

function zusammenfassung(befunde: Record<string, unknown[]>): string {
    const anzahl = Object.keys(befunde).length
    const mitBefunden = Object.values(befunde).filter(liste => liste.length > 0).length
    const uebernommen = anzahl === 1 ? t('ausbilder.einesUebernommen') : t('ausbilder.uebernommen', {anzahl})
    return mitBefunden > 0 ? `${uebernommen} ${t('ausbilder.mitBefunden', {befunde: mitBefunden})}` : uebernommen
}

function zeige(text: string, istFehler: boolean): void {
    meldung.value = text
    fehler.value = istFehler
}
</script>

<template>
    <div class="flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-2">
            <a :href="`/api/uebung/${encodeURIComponent(code)}/pool`" download="calltaker-pool.json" class="rounded border border-slate-400 px-3 py-1.5 text-sm font-semibold no-underline" @click="emit('exportiert')">{{ t('ausbilder.export') }}</a>
            <label class="cursor-pointer rounded border border-slate-400 px-3 py-1.5 text-sm font-semibold">
                {{ t('ausbilder.import') }}
                <input type="file" accept="application/json,.json" class="sr-only" @change="hochladen"/>
            </label>
            <label class="flex items-center gap-1.5 text-sm">
                {{ t('ausbilder.modus') }}
                <select v-model="modus" class="rounded border border-slate-400 px-1.5 py-1">
                    <option value="anhaengen">{{ t('ausbilder.anhaengen') }}</option>
                    <option value="ersetzen">{{ t('ausbilder.ersetzen') }}</option>
                </select>
            </label>
        </div>
        <p v-if="meldung" :role="fehler ? 'alert' : 'status'" :class="['m-0 whitespace-pre-line text-sm', fehler ? 'text-fehler' : 'text-ok']">{{ meldung }}</p>
    </div>
</template>
