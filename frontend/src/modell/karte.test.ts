import {describe, expect, it} from 'vitest'
import {abstandMeter} from './karte'

describe('abstandMeter', () => {
    it('misst die Strecke zwischen zwei Punkten', () => {
        expect(abstandMeter([52.52, 13.405], [52.52, 13.405])).toBe(0)
        expect(abstandMeter([52.5163, 13.3777], [52.5200, 13.4050])).toBeCloseTo(1890, -1)
    })
})
