import {getCurrentInstance, onBeforeUnmount, ref, watch} from 'vue'

/**
 * A metronome: counts beats while it runs and, unless muted, clicks on each one through WebAudio.
 * Beats are scheduled against the monotonic clock so they do not drift; beats missed while timers
 * were held back, as in a background tab, are skipped rather than played in a burst. Audio may
 * only start after a user gesture, so the first click or key press anywhere unlocks it.
 * With `beatmungAlle` set, every that many-th beat is a breath instead of a compression, as in
 * newborn CPR (three compressions, one breath): it sounds lower and is not counted.
 *
 * @param laeuft whether it runs
 * @param takt beats a minute
 * @param stumm whether it stays silent
 * @param beatmungAlle every how many beats one is a breath, 0 for none
 * @returns the compressions since the last start, whether the current beat is a breath, whether
 * audio is unlocked, and `freischalten` to call from a click so audio may play
 */
export function useTaktgeber(laeuft: () => boolean, takt: () => number, stumm: () => boolean, beatmungAlle: () => number = () => 0) {
    const schlaege = ref(0)
    const beatmung = ref(false)
    const hoerbar = ref(false)
    let takte = 0
    let kontext: AudioContext | undefined
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    let naechster = 0

    function freischalten(): void {
        if (stumm() || typeof AudioContext === 'undefined') return
        kontext ??= new AudioContext()
        void kontext.resume()
        hoerbar.value = true
    }

    function klicken(hoehe: number): void {
        if (stumm() || !kontext) return
        const ton = kontext.createOscillator()
        const lautstaerke = kontext.createGain()
        const ab = kontext.currentTime
        ton.frequency.value = hoehe
        lautstaerke.gain.setValueAtTime(0.4, ab)
        lautstaerke.gain.exponentialRampToValueAtTime(0.001, ab + 0.05)
        ton.connect(lautstaerke).connect(kontext.destination)
        ton.start(ab)
        ton.stop(ab + 0.06)
    }

    function schlag(): void {
        takte++
        const alle = beatmungAlle()
        beatmung.value = alle > 0 && takte % alle === 0
        if (!beatmung.value) schlaege.value++
        klicken(beatmung.value ? 500 : 1000)
        const abstand = 60000 / takt()
        naechster = Math.max(naechster + abstand, performance.now())
        zeitgeber = setTimeout(schlag, Math.max(0, naechster - performance.now()))
    }

    function anhalten(): void {
        clearTimeout(zeitgeber)
        zeitgeber = undefined
    }

    function beiGeste(): void {
        freischalten()
        if (kontext) entfernen()
    }

    function entfernen(): void {
        window.removeEventListener('pointerdown', beiGeste)
        window.removeEventListener('keydown', beiGeste)
    }

    window.addEventListener('pointerdown', beiGeste)
    window.addEventListener('keydown', beiGeste)

    watch(beatmungAlle, () => {
        takte = 0
    })

    watch(laeuft, an => {
        anhalten()
        if (!an) return
        schlaege.value = 0
        takte = 0
        naechster = performance.now()
        schlag()
    }, {immediate: true})

    if (getCurrentInstance()) onBeforeUnmount(() => {
        anhalten()
        entfernen()
        void kontext?.close()
    })
    return {schlaege, beatmung, hoerbar, freischalten}
}
