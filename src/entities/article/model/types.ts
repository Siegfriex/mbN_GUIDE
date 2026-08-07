import type { Locale } from '../../../shared/i18n'
import type { ProvenanceSource } from '../../place'

export type Article = {
  id: string
  sourceArticleId: string
  source: ProvenanceSource
  url?: string
  rawTitle: string
  cleanTitle: string
  localized: Record<Locale, { headline: string; excerpt: string }>
  publishedAt?: string
  category: string
  tags: string[]
  placeIds: string[]
  storyIds: string[]
  status: 'active' | 'unavailable'
  provenance: {
    source: ProvenanceSource
    referenceId: string
    label: Record<Locale, string>
    method: 'fixture' | 'editorial' | 'release'
  }
}

export function getArticleContent(article: Article, locale: Locale) {
  return article.localized[locale] ?? article.localized.en
}
