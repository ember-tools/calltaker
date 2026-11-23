import {getCurrentInstance, onBeforeUnmount, ref, watch, type Ref} from 'vue'

const SPEICHER = 'calltaker.klingelton'

/**
 * A ring tone while calls wait, which the trainee can switch off; the choice is remembered in
 * this browser.
 *
 * @param klingelt whether a call is waiting for the trainee
 * @returns whether the tone is switched on
 */
export function useKlingelton(klingelt: Ref<boolean>) {
    const an = ref(gespeichert())
    let kontext: AudioContext | null = null
    let zeitgeber: ReturnType<typeof setInterval> | undefined

    function ton(): void {
        kontext ??= new AudioContext()
        const oszillator = kontext.createOscillator()
        const lautstaerke = kontext.createGain()
        oszillator.frequency.value = 880
        lautstaerke.gain.value = 0.08
        oszillator.connect(lautstaerke).connect(kontext.destination)
        oszillator.start()
        oszillator.stop(kontext.currentTime + 0.35)
    }

    function stellen(): void {
        clearInterval(zeitgeber)
        zeitgeber = undefined
        if (!klingelt.value || !an.value || typeof AudioContext === 'undefined') return
        ton()
        zeitgeber = setInterval(ton, 1500)
    }

    watch([klingelt, an], stellen, {immediate: true})
    watch(an, wert => {
        try {
            localStorage.setItem(SPEICHER, wert ? 'an' : 'aus')
        } catch {
            return
        }
    })
    if (getCurrentInstance()) onBeforeUnmount(() => clearInterval(zeitgeber))
    return an
}

/**
 * Whether the tone was switched off in this browser before.
 *
 * @returns false only when it was switched off
 */
function gespeichert(): boolean {
    try {
        return localStorage.getItem(SPEICHER) !== 'aus'
    } catch {
        return true
    }
}
