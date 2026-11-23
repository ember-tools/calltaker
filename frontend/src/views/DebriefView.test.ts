import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {ref, shallowRef} from 'vue'
import {i18n} from '../i18n'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import {sichtVon} from '../modell/uebung'
import DebriefView from './DebriefView.vue'

const beendet = anrufMit('b', 'beendet')
const aufgelegt = anrufMit('x', 'aufgelegt')
const traineeZustand = {
    verbunden: {ausbilder: true, trainee: true},
    engine: {gestartet: true, pausiert: false, automatischPausiert: false},
    anrufe: [{...sichtVon(beendet), szenario: beendet.szenario}, {...sichtVon(aufgelegt), eintraege: undefined}, sichtVon(anrufMit('l'))],
}

vi.mock('../composables/useUebung', () => ({useUebung: () => ({zustand: ref(traineeZustand), erreichbar: ref(true), unbekannt: ref(false), absicht: vi.fn()})}))
vi.mock('../composables/useAbfragegraph', () => ({useAbfragegraph: () => ({graph: shallowRef(GRAPH), schwerste: shallowRef(new Map()), fehler: shallowRef(null)})}))

/**
 * Mounts the trainee's debrief of a call.
 *
 * @param anrufId the call
 * @returns the mounted view
 */
async function debriefVon(anrufId: string) {
    const ansicht = mount(DebriefView, {props: {code: 'T-1', anrufId, rolle: 'trainee'}, global: {plugins: [i18n], stubs: {RouterLink: true}}})
    await flushPromises()
    return ansicht
}

describe('DebriefView', () => {
    it('zeigt dem Trainee die Wahrheit eines beendeten Anrufs', async () => {
        const ansicht = await debriefVon('b')
        expect(ansicht.text()).toContain('Sturz b')
        expect(ansicht.text()).toContain('17D01')
    })

    it('hat für einen aufgelegten oder laufenden Anruf keinen Debrief', async () => {
        expect((await debriefVon('x')).text()).toContain('Für diesen Anruf gibt es keinen Debrief')
        expect((await debriefVon('l')).text()).toContain('Für diesen Anruf gibt es keinen Debrief')
    })
})
