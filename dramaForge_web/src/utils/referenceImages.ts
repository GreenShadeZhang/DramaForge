import type { RefImage } from '@/types/character'

export type ReferenceImage = string | RefImage | null | undefined

export function referenceImageUrl(image: ReferenceImage): string {
  if (!image) return ''
  return typeof image === 'string' ? image : image.url || ''
}

export function firstReferenceImageUrl(images?: ReferenceImage[] | null): string {
  return referenceImageUrl(images?.[0])
}
