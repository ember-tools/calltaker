import {leereEintraege} from './eintraege'
import {antwortenAusPfad, leererEntwurf} from './szenarioentwurf'
import {BIS_SITUATION, testgraph} from './testgraph.test-hilfe'
import type {Anruf, AusbilderZustand} from './uebung'

/** The small test graph shared by the trainer view tests. */
export const GRAPH = testgraph()

/**
 * A call of the test graph whose truth ends at 17D01.
 *
 * @param id the call's id
 * @param zustand where the call stands
 * @returns the call
 */
export function anrufMit(id: string, zustand: Anruf['zustand'] = 'gespraech'): Anruf {
    return {
        id, zustand, klingeltSeit: 1000, angenommenUm: 1030, beendetUm: zustand === 'beendet' || zustand === 'aufgelegt' ? 1100 : undefined,
        eintraege: leereEintraege(),
        szenario: {
            ...leererEntwurf(1), id: `s${id}`, titel: `Sturz ${id}`,
            ort: {adresse: {strasse: 'Werderstraße', hausnummer: '20', plz: '13587', ortsteil: 'Hakenfelde'}, koordinaten: [52.5663, 13.2122], objekt: '', geschoss: '2. OG', klingel: 'Kaya', anfahrt: '', gefahren: ''},
            anrufer: {name: 'Mehmet Kaya', rufnummerUnterdrueckt: false, rufnummer: '491761234567', rueckrufnummer: '493012345678'},
            antworten: antwortenAusPfad(GRAPH, [...BIS_SITUATION, {knoten: 'p.k0', antwort: 'schwer'}]),
            ziel: {knoten: 'p.e2', code: '17D01'},
            rolle: {stimmung: 'panisch', sprache: '', notizen: 'Weint.'},
        },
    }
}

/**
 * A trainer's state holding the given calls.
 *
 * @param anrufe the calls
 * @returns the state
 */
export function zustandMit(anrufe: Anruf[]): AusbilderZustand {
    return {
        codes: {ausbilder: 'A-1', trainee: 'T-1'},
        verbunden: {ausbilder: true, trainee: true},
        engine: {
            gestartet: true, pausiert: false, automatischPausiert: false, manuellPausiert: false, naechstesKlingeln: null,
            parameter: {erstesKlingelnMin: 5, erstesKlingelnMax: 10, basisAbstand: 45, abstandFaktor: 1.6, maxSchlange: 5, geduldMin: 60, geduldMax: 300, zurueckInPool: true, autoGenerieren: true, zielReanimation: 120, zielUebergabe: 60},
        },
        pool: [anrufMit('p').szenario],
        poolBefunde: {},
        poolStand: 0,
        erzeugung: {gewichtRd: 80, gewichtBrand: 12, gewichtTh: 8, kategorie: '', ortsteil: '', bezirk: '', anteilOrte: 30},
        anrufe,
        spiegel: {},
    }
}
