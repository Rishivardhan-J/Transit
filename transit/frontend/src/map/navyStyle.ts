import type { Map as MapboxMap } from 'mapbox-gl'
import { colors } from '../design-system/tokens'

/**
 * Retint Mapbox's dark-v11 to Command Navy at runtime (no Mapbox Studio account needed):
 * background/land -> dominant, water -> deeper navy, roads -> secondary/border, labels -> text-secondary.
 */
export function retintToCommandNavy(map: MapboxMap): void {
  const style = map.getStyle()
  if (!style?.layers) return
  const set = (id: string, prop: string, value: string) => { try { map.setPaintProperty(id, prop as 'background-color', value) } catch { /* layer lacks that property */ } }
  for (const layer of style.layers) {
    const id = layer.id
    const t = layer.type
    if (t === 'background') set(id, 'background-color', colors.surface.dominant)
    else if (t === 'fill') {
      if (/water/.test(id)) set(id, 'fill-color', '#0B1220')
      else if (/park|green|wood|grass|national/.test(id)) set(id, 'fill-color', '#122033')
      else if (/building/.test(id)) set(id, 'fill-color', colors.surface.secondary)
      else if (/land|landuse|pitch|sand|hospital|school|airport/.test(id)) set(id, 'fill-color', '#131C31')
    } else if (t === 'line') {
      if (/water/.test(id)) set(id, 'line-color', '#0B1220')
      else if (/road|bridge|tunnel|street|motorway|trunk|primary|secondary|tertiary|path|pedestrian/.test(id)) {
        set(id, 'line-color', /case|casing/.test(id) ? colors.surface.dominant : /motorway|trunk|primary/.test(id) ? colors.border.hover : colors.border.default)
      } else if (/admin|boundary/.test(id)) set(id, 'line-color', colors.border.hover)
    } else if (t === 'symbol') {
      set(id, 'text-color', colors.text.secondary)
      set(id, 'text-halo-color', colors.surface.dominant)
    }
  }
}
