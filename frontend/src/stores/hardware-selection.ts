import type { Fields } from '../types'

export function initialHardwareIds(hardware: Fields[], tilesimReady: boolean) {
  if (hardware.some(item => item.group === 'remote')) return hardware.filter(item => item.group === 'remote').map(item => item.id as string)
  return hardware
    .filter(item => item.group === 'demo' || (tilesimReady && item.group === 'tilesim'))
    .map(item => item.id as string)
}
