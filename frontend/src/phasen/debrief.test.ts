import {describe, expect, it} from 'vitest'
import {anrufMit, GRAPH} from '../modell/ausbilder.test-hilfe'
import {BIS_SITUATION} from '../modell/testgraph.test-hilfe'
import {sichtVon} from '../modell/uebung'
import {debrief, zeitenVon} from './debrief'

describe('debrief', () => {
    it('rechnet die Zeiten und nennt, was beim Beenden fehlte', () => {
        const anruf = anrufMit('a', 'beendet')
        anruf.eintraege.zeiten = {adresse: 1050}
        anruf.eintraege.abfrage.pfad = [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]
        anruf.eintraege.anrufer = {name: 'Mehmet Kaya', rufnummerBestaetigt: false, rueckrufnummer: ''}
        const sicht = sichtVon(anruf)
        expect(zeitenVon(sicht)).toEqual({annahme: 30, adresse: 20, code: undefined, gespraech: 70})
        const ergebnis = debrief(GRAPH, sicht, anruf.szenario)
        expect(ergebnis.fehlend).toEqual(['fehlt.einsatzort', 'fehlt.rueckrufnummer'])
        const code = ergebnis.phasen.flatMap(p => p.bewertungen).find(b => b.feld === 'bewertung.code')!
        expect(code).toMatchObject({urteil: 'teilweise', stufe: 'protokoll'})
        expect(ergebnis.pfad.abzweigung?.knoten).toBe('p.k0')
    })
})
