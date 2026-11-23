import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {ref, shallowRef} from 'vue'
import {i18n} from '../i18n'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {sichtVon} from '../modell/uebung'
import TraineeView from './TraineeView.vue'

const gespraech = sichtVon(anrufMit('g'))
gespraech.eintraege!.ort.koordinaten = [52.5, 13.4]

vi.mock('../composables/useUebung', () => ({useUebung: () => ({
    zustand: ref({verbunden: {ausbilder: true, trainee: true}, engine: {gestartet: true, pausiert: false, automatischPausiert: false}, anrufe: [gespraech]}),
    erreichbar: ref(true), unbekannt: ref(false), absicht: vi.fn().mockResolvedValue({}),
})}))
vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(GRAPH), schwerste: shallowRef(schwersteErreichbare(GRAPH)), fehler: shallowRef(null)})}))
vi.mock('../components/KarteLeaflet.vue', () => ({default: {template: '<div/>'}}))
vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))

describe('TraineeView mit der Tastatur', () => {
    it('wechselt mit F3 in die Abfrage und mit F2 zurück in die Maske', async () => {
        const ansicht = mount(TraineeView, {props: {code: 'T-1'}, global: {plugins: [i18n], stubs: {RouterLink: true}}, attachTo: document.body})
        await flushPromises()
        window.dispatchEvent(new KeyboardEvent('keydown', {key: 'F3'}))
        expect(document.activeElement?.closest('[data-antworten]')).not.toBeNull()
        window.dispatchEvent(new KeyboardEvent('keydown', {key: 'F2'}))
        expect(document.activeElement?.getAttribute('role')).toBe('combobox')
        expect(ansicht.text()).toContain('F2: Einsatzmaske · F3: Abfrage')
        ansicht.unmount()
    })
})
