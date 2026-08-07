import type { Locale } from '../../../shared/i18n'

export const PLACE_CATEGORIES = [
  'performance',
  'exhibition',
  'music',
  'food',
  'beauty-fashion',
  'broadcast-media',
  'healing',
  'activity',
] as const

export type PlaceCategory = (typeof PLACE_CATEGORIES)[number]
export type PlaceStatus = 'active' | 'unavailable'
export type ProvenanceSource = 'mbn' | 'editor' | 'partner' | 'community' | 'public'

export type LocalizedPlaceContent = {
  name: string
  summary: string
  whyItMatters: string
  availableExperience: string
}

export type PlaceProvenance = {
  source: ProvenanceSource
  referenceId: string
  label: Record<Locale, string>
  method: 'fixture' | 'editorial' | 'release'
  reviewedAt?: string
  isSponsored: boolean
}

export type Place = {
  id: string
  slug: string
  coordinates: { lat: number; lng: number }
  address: Record<Locale, string>
  category: PlaceCategory
  tags: string[]
  availableFrom?: string
  availableTo?: string
  localized: Record<Locale, LocalizedPlaceContent>
  localeSupport: Locale[]
  source: ProvenanceSource
  provenance: PlaceProvenance
  relatedStoryIds: string[]
  relatedLiveIds: string[]
  offerIds: string[]
  status: PlaceStatus
}

export function getPlaceContent(place: Place, locale: Locale) {
  return place.localized[locale] ?? place.localized.en
}
