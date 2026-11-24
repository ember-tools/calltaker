import type {Eintraege} from './eintraege'
import type {Befund, Szenario} from './szenario'
import type {Zielzeiten} from './zeit'

/** Which role a code stands for. */
export type Rolle = 'ausbilder' | 'trainee'

/** Where a call stands. */
export type Anrufzustand = 'wartet' | 'gespraech' | 'beendet' | 'aufgelegt'

/** Whether each role polled within the last seconds. */
export interface Verbunden {
    ausbilder: boolean
    trainee: boolean
}

/** A call as the trainee sees it: the truth only once it has ended. */
export interface AnrufSicht {
    id: string
    zustand: Anrufzustand
    klingeltSeit: number
    rufnummer?: string
    rufnummerUnterdrueckt: boolean
    angenommenUm?: number
    beendetUm?: number
    /** When the crews reach a cardiac arrest, once CPR guidance has started. */
    eintreffenUm?: number
    eintraege?: Eintraege
    szenario?: Szenario
    /** The trainer's corrections of which instructions were given, once the call has ended. */
    korrektur?: Record<string, boolean>
}

/** A call as the trainer sees it, truth included. */
export interface Anruf {
    id: string
    szenario: Szenario
    zustand: Anrufzustand
    klingeltSeit: number
    angenommenUm?: number
    beendetUm?: number
    /** When the crews reach a cardiac arrest, once CPR guidance has started. */
    eintreffenUm?: number
    eintraege: Eintraege
    /** The trainer's corrections of which instructions to the caller were given. */
    korrektur?: Record<string, boolean>
}

/** The state of an exercise as the trainee sees it. */
export interface TraineeZustand {
    verbunden: Verbunden
    engine: EngineSicht
    anrufe: AnrufSicht[]
}

/** The state of an exercise as the trainer sees it. */
export interface AusbilderZustand {
    codes: {ausbilder: string, trainee: string}
    verbunden: Verbunden
    engine: EngineZustand
    pool: Szenario[]
    /** What the graph check found, for the scenarios of the pool that have findings. */
    poolBefunde: Record<string, Befund[]>
    /** Counts the trainer's changes to the pool; drawing and returning by the engine leave it. */
    poolStand: number
    erzeugung: Erzeugung
    anrufe: Anruf[]
    spiegel: Record<string, unknown>
}

/** The state of an exercise for a role. */
export type ZustandFuer<R extends Rolle> = R extends 'ausbilder' ? AusbilderZustand : TraineeZustand

/** The queue engine's settings, which the trainer may change. */
export interface EngineParameter {
    erstesKlingelnMin: number
    erstesKlingelnMax: number
    basisAbstand: number
    abstandFaktor: number
    maxSchlange: number
    geduldMin: number
    geduldMax: number
    zurueckInPool: boolean
    /** Whether an empty pool makes up scenarios instead of leaving the queue quiet. */
    autoGenerieren: boolean
    zielReanimation: number
    zielUebergabe: number
}

/** What the trainer sets for made-up scenarios: weights per discipline, a category, an area. */
export interface Erzeugung {
    gewichtRd: number
    gewichtBrand: number
    gewichtTh: number
    kategorie: string
    ortsteil: string
    bezirk: string
    /** The share of scenarios, in percent, that happen at a named place rather than a door. */
    anteilOrte: number
}

/** The queue engine's state as the trainee sees it. */
export interface EngineSicht {
    gestartet: boolean
    pausiert: boolean
    automatischPausiert: boolean
    pausiertSeit?: number
    ziele?: Zielzeiten
}

/** The queue engine's state as the trainer sees it. */
export interface EngineZustand extends EngineSicht {
    manuellPausiert: boolean
    naechstesKlingeln: number | null
    parameter: EngineParameter
}

/**
 * A call as the trainee's screen shows it, made from the trainer's copy, for the live mirror.
 *
 * @param anruf the call with its truth
 * @returns the call as the trainee sees it during the conversation
 */
export function sichtVon(anruf: Anruf): AnrufSicht {
    const anrufer = anruf.szenario.anrufer
    return {
        id: anruf.id,
        zustand: anruf.zustand,
        klingeltSeit: anruf.klingeltSeit,
        rufnummer: anrufer.rufnummerUnterdrueckt ? undefined : anrufer.rufnummer,
        rufnummerUnterdrueckt: anrufer.rufnummerUnterdrueckt,
        angenommenUm: anruf.angenommenUm,
        beendetUm: anruf.beendetUm,
        eintraege: anruf.eintraege,
        korrektur: anruf.korrektur,
        eintreffenUm: anruf.eintreffenUm,
    }
}
