import type {Abfragegraph} from './abfragegraph'
import {leereEintraege, type Eintraege} from './eintraege'
import type {Szenario} from './szenario'
import type {Anruf, AnrufSicht, TraineeZustand} from './uebung'

const NUMMER = '4915112345678'

/**
 * A queue with two waiting calls, one with a hidden number, as the help page shows it.
 *
 * @param jetzt the present in seconds
 * @returns the trainee's state
 */
export function beispielSchlange(jetzt: number): TraineeZustand {
    return {
        verbunden: {ausbilder: true, trainee: true},
        engine: {gestartet: true, pausiert: false, automatischPausiert: false},
        anrufe: [
            {id: 'hilfe-1', zustand: 'wartet', klingeltSeit: jetzt - 42, rufnummer: NUMMER, rufnummerUnterdrueckt: false},
            {id: 'hilfe-2', zustand: 'wartet', klingeltSeit: jetzt - 12, rufnummerUnterdrueckt: true},
        ],
    }
}

/**
 * A call in conversation from a mobile number, with its cell.
 *
 * @param jetzt the present in seconds
 * @returns the call as the trainee sees it
 */
export function beispielAnruf(jetzt: number): AnrufSicht {
    return {
        id: 'hilfe-3', zustand: 'gespraech', klingeltSeit: jetzt - 70, angenommenUm: jetzt - 55,
        rufnummer: NUMMER, rufnummerUnterdrueckt: false,
        funkzelle: {mitte: [52.4851, 13.4258], radius: 900},
    }
}

/**
 * Entries in the middle of a medical call: caller, address and point taken, the questioning begun.
 *
 * @param graph the graph
 * @returns the entries
 */
export function beispielEintraege(graph: Abfragegraph): Eintraege {
    const eintraege = leereEintraege()
    eintraege.anrufer = {name: 'Ines Wagner', rufnummerBestaetigt: true, rueckrufnummer: NUMMER}
    eintraege.ort = {
        ...eintraege.ort,
        adresse: {strasse: 'Karl-Marx-Straße', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln'},
        koordinaten: [52.4815, 13.4352],
        geschoss: '2. OG',
        klingel: 'Wagner',
    }
    eintraege.abfrage = {pfad: [{knoten: graph.meta.wurzel, antwort: 'rd'}]}
    return eintraege
}

/**
 * Entries during CPR guidance: no certain signs of death, the beat started a minute ago.
 *
 * @param jetzt the present in seconds
 * @returns the entries
 */
export function beispielReanimation(jetzt: number): Eintraege {
    return {
        ...leereEintraege(),
        abfrage: {pfad: [{knoten: 'rd.09.todeszeichen', antwort: 'keine'}]},
        reanimation: {laeuft: true, takt: 100},
        zeiten: {reanimation: jetzt - 60},
    }
}

/**
 * A call with its truth, as the trainer's truth card shows it during the conversation.
 *
 * @param graph the graph
 * @param jetzt the present in seconds
 * @returns the call
 */
export function beispielWahrheit(graph: Abfragegraph, jetzt: number): Anruf {
    const ziel = graph.endpunkte.find(e => e.code === '17A01') ?? graph.endpunkte[0]
    const szenario: Szenario = {
        id: 'hilfe-s', version: 1, abfrageVersion: graph.meta.version, titel: `${(ziel ? graph.knoten[ziel.knoten]?.anlass : undefined) ?? 'Sturz'}, Neukölln`, herkunft: 'generiert',
        ort: {
            adresse: {strasse: 'Karl-Marx-Straße', hausnummer: '92', plz: '12043', ortsteil: 'Neukölln'},
            koordinaten: [52.4815, 13.4352], objekt: '', geschoss: '2. OG', klingel: 'Wagner', anfahrt: '', gefahren: '', haustier: 'ein Hund',
        },
        anrufer: {name: 'Ines Wagner', rufnummer: NUMMER, rufnummerUnterdrueckt: false},
        betroffener: {name: 'Ines Wagner'},
        antworten: {
            'eroeffnung.hand': {antwort: '1-hand-der-anrufer-ist-selbst-betroffen'},
            'rd.alter': {wert: '78'},
        },
        ziel: {knoten: ziel?.knoten ?? '', code: ziel?.code ?? ''},
        rolle: {stimmung: 'aufgeregt', sprache: '', notizen: ''},
        erweiterungen: {},
    }
    return {id: 'hilfe-4', szenario, zustand: 'gespraech', klingeltSeit: jetzt - 70, angenommenUm: jetzt - 55, eintraege: beispielEintraege(graph)}
}
