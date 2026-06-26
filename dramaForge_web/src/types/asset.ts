import type { CharacterRole } from './enums'
import type { RefImage } from './character'

export type AssetLibraryType = 'character' | 'scene'
export type AssetLibraryImage = string | RefImage

export interface AssetLibraryItem {
  id: number
  uid: string
  type: AssetLibraryType
  project_id: number
  name: string
  role?: CharacterRole | null
  source?: string
  description?: string
  voice_desc?: string
  time_of_day?: string | null
  interior?: boolean | null
  reference_images: AssetLibraryImage[]
  created_at: string
}
