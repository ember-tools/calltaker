import type {Eintraege} from './eintraege'
import type {Szenario} from './szenario'

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
    eintraege?: Eintraege
    szenario?: Szenario
}

/** A call as the trainer sees it, truth included. */
export interface Anruf {
    id: string
    szenario: Szenario
    zustand: Anrufzustand
    klingeltSeit: number
    angenommenUm?: number
    beendetUm?: number
    eintraege: Eintraege
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
}

/** The queue engine's state as the trainee sees it. */
export interface EngineSicht {
    gestartet: boolean
    pausiert: boolean
    automatischPausiert: boolean
    pausiertSeit?: number
}

/** The queue engine's state as the trainer sees it. */
export interface EngineZustand extends EngineSicht {
    manuellPausiert: boolean
    naechstesKlingeln: number | null
    parameter: EngineParameter
}
