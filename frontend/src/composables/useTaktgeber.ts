import {getCurrentInstance, onBeforeUnmount, ref, watch} from 'vue'

/**
 * A metronome: counts beats while it runs and, unless muted, clicks on each one through WebAudio.
 * Beats are scheduled against the monotonic clock so they do not drift; beats missed while timers
 * were held back, as in a background tab, are skipped rather than played in a burst. Audio may
 * only start after a user gesture, so the first click or key press anywhere unlocks it.
 *
 * @param laeuft whether it runs
 * @param takt beats a minute
 * @param stumm whether it stays silent
 * @returns the beats since the last start, and `freischalten` to call from a click so audio may play
 */
export function useTaktgeber(laeuft: () => boolean, takt: () => number, stumm: () => boolean) {
    const schlaege = ref(0)
    let kontext: AudioContext | undefined
    let zeitgeber: ReturnType<typeof setTimeout> | undefined
    let naechster = 0

    function freischalten(): void {
        if (stumm() || typeof AudioContext === 'undefined') return
        kontext ??= new AudioContext()
        void kontext.resume()
    }

    function klicken(): void {
        if (stumm() || !kontext) return
        const ton = kontext.createOscillator()
        const lautstaerke = kontext.createGain()
        const ab = kontext.currentTime
        ton.frequency.value = 1000
        lautstaerke.gain.setValueAtTime(0.4, ab)
        lautstaerke.gain.exponentialRampToValueAtTime(0.001, ab + 0.05)
        ton.connect(lautstaerke).connect(kontext.destination)
        ton.start(ab)
        ton.stop(ab + 0.06)
    }

    function schlag(): void {
        schlaege.value++
        klicken()
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

    watch(laeuft, an => {
        anhalten()
        if (!an) return
        schlaege.value = 0
        naechster = performance.now()
        schlag()
    }, {immediate: true})

    if (getCurrentInstance()) onBeforeUnmount(() => {
        anhalten()
        entfernen()
        void kontext?.close()
    })
    return {schlaege, freischalten}
}
