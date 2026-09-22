import type { Fields } from '../types'

export function initialHardwareIds(hardware: Fields[], tilesimReady: boolean) {
  return hardware
    .filter(item => item.group === 'demo' || (tilesimReady && item.group === 'tilesim'))
    .map(item => item.id as string)
}
