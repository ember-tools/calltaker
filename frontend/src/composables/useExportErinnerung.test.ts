import {describe, expect, it} from 'vitest'
import {nextTick, ref} from 'vue'
import {useExportErinnerung} from './useExportErinnerung'

describe('useExportErinnerung', () => {
    it('warnt beim Verlassen nur, solange der Ausbilder seit dem Herunterladen etwas geändert hat', async () => {
        const stand = ref<number | undefined>(undefined)
        const {geaendert, exportiert} = useExportErinnerung(stand)
        stand.value = 3
        await nextTick()
        expect(geaendert.value).toBe(false)
        stand.value = 4
        await nextTick()
        expect(geaendert.value).toBe(true)
        const verlassen = new Event('beforeunload', {cancelable: true})
        window.dispatchEvent(verlassen)
        expect(verlassen.defaultPrevented).toBe(true)
        exportiert()
        expect(geaendert.value).toBe(false)
    })
})
