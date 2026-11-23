import {describe, expect, it} from 'vitest'
import {leereEintraege} from '../modell/eintraege'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import type {AnrufSicht} from '../modell/uebung'
import {nochOffen, phasenstand} from './register'

const anruf: AnrufSicht = {id: 'a', zustand: 'gespraech', klingeltSeit: 0, rufnummer: '493012345', rufnummerUnterdrueckt: false}
const kontext = {graph: testgraph(), anruf}

describe('phasen', () => {
    it('beginnt mit dem Standort und nennt alles Offene', () => {
        const eintraege = leereEintraege()
        expect(phasenstand(eintraege, kontext).map(s => s.phase.id)).toEqual(['standort', 'abfrage', 'personalien'])
        expect(nochOffen(eintraege, kontext)).toEqual(['fehlt.einsatzort', 'fehlt.code', 'fehlt.name', 'fehlt.rueckrufnummer'])
    })

    it('ist vollständig mit Punkt, Code, Name und bestätigter Nummer', () => {
        const eintraege = leereEintraege()
        eintraege.ort.koordinaten = [52.5, 13.4]
        eintraege.abfrage.pfad = [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'leicht'}]
        eintraege.anrufer.name = 'Ayşe Yılmaz'
        eintraege.anrufer.rufnummerBestaetigt = true
        eintraege.anrufer.rueckrufnummer = '493012345'
        expect(nochOffen(eintraege, kontext)).toEqual([])
    })

    it('verlangt bei unterdrückter Nummer eine Rückrufnummer, eine Bestätigung reicht nicht', () => {
        const eintraege = leereEintraege()
        eintraege.anrufer.rufnummerBestaetigt = true
        const unterdrueckt = {...kontext, anruf: {...anruf, rufnummer: undefined, rufnummerUnterdrueckt: true}}
        expect(nochOffen(eintraege, unterdrueckt)).toContain('fehlt.rueckrufnummer')
        eintraege.anrufer.rueckrufnummer = 'abc'
        expect(nochOffen(eintraege, unterdrueckt)).toContain('fehlt.rueckrufnummer')
        eintraege.anrufer.rueckrufnummer = '0176 1234567'
        expect(nochOffen(eintraege, unterdrueckt)).not.toContain('fehlt.rueckrufnummer')
    })
})
