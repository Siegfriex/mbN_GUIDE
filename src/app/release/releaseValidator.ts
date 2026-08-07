import { CONSUMED_CONTRACT } from '../config'
import type { ReleaseBundle, ReleaseValidationResult } from './types'

export const REQUIRED_RELEASE_FILE_PATHS = [
  'places.json',
  'articles.json',
  'stories.json',
  'live_sessions.json',
  'offers.json',
  'article_place_relations.json',
  'article_article_relations.json',
  'article_live_relations.json',
  'place_live_relations.json',
  'recommendations.json',
  'taxonomy.json',
  'quality_report.json',
] as const

async function sha256(bytes: Uint8Array) {
  const copy = new Uint8Array(bytes)
  const digest = await crypto.subtle.digest('SHA-256', copy.buffer)
  return Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('')
}

export async function validateReleaseBundle(bundle: ReleaseBundle): Promise<ReleaseValidationResult> {
  const errors: string[] = []
  const { manifest, files, projection } = bundle
  const versions = CONSUMED_CONTRACT.versions

  if (!manifest.releaseId) errors.push('MANIFEST_RELEASE_ID_MISSING')
  if (manifest.qualityStatus !== 'PASS') errors.push('MANIFEST_QUALITY_NOT_PASS')
  if (manifest.contractVersion !== versions.data) errors.push('CONTRACT_VERSION_MISMATCH')
  if (manifest.schemaVersion !== versions.data) errors.push('SCHEMA_VERSION_MISMATCH')
  if (manifest.taxonomyVersion !== versions.data) errors.push('TAXONOMY_VERSION_MISMATCH')

  for (const requiredPath of REQUIRED_RELEASE_FILE_PATHS) {
    const declared = manifest.files.find((file) => file.path === requiredPath)
    if (!declared?.required) errors.push(`REQUIRED_FILE_UNDECLARED:${requiredPath}`)
  }

  for (const file of manifest.files) {
    const bytes = files[file.path]
    if (!bytes) {
      if (file.required) errors.push(`DECLARED_FILE_MISSING:${file.path}`)
      continue
    }
    if ((await sha256(bytes)) !== file.sha256) errors.push(`FILE_SHA_MISMATCH:${file.path}`)
  }

  const ids = {
    place: new Set(projection.places.map((item) => item.id)),
    article: new Set(projection.articles.map((item) => item.id)),
    story: new Set(projection.stories.map((item) => item.id)),
    live: new Set(projection.liveSessions.map((item) => item.id)),
  }

  for (const place of projection.places) {
    if (!place.localized.ko || !place.localized.en) errors.push(`PLACE_LOCALE_MISSING:${place.id}`)
    if (!place.provenance?.referenceId) errors.push(`PLACE_PROVENANCE_MISSING:${place.id}`)
    place.relatedStoryIds.forEach((id) => !ids.story.has(id) && errors.push(`PLACE_STORY_FK_BROKEN:${place.id}:${id}`))
    place.relatedLiveIds.forEach((id) => !ids.live.has(id) && errors.push(`PLACE_LIVE_FK_BROKEN:${place.id}:${id}`))
  }
  for (const story of projection.stories) {
    if (!story.localized.ko || !story.localized.en) errors.push(`STORY_LOCALE_MISSING:${story.id}`)
    if (!story.provenance?.referenceId) errors.push(`STORY_PROVENANCE_MISSING:${story.id}`)
    story.articleIds.forEach((id) => !ids.article.has(id) && errors.push(`STORY_ARTICLE_FK_BROKEN:${story.id}:${id}`))
    story.placeIds.forEach((id) => !ids.place.has(id) && errors.push(`STORY_PLACE_FK_BROKEN:${story.id}:${id}`))
    story.liveIds.forEach((id) => !ids.live.has(id) && errors.push(`STORY_LIVE_FK_BROKEN:${story.id}:${id}`))
  }
  for (const article of projection.articles) {
    if (!article.localized.ko || !article.localized.en) errors.push(`ARTICLE_LOCALE_MISSING:${article.id}`)
    if (!article.provenance?.referenceId) errors.push(`ARTICLE_PROVENANCE_MISSING:${article.id}`)
    article.placeIds.forEach((id) => !ids.place.has(id) && errors.push(`ARTICLE_PLACE_FK_BROKEN:${article.id}:${id}`))
    article.storyIds.forEach((id) => !ids.story.has(id) && errors.push(`ARTICLE_STORY_FK_BROKEN:${article.id}:${id}`))
  }
  for (const session of projection.liveSessions) {
    if (!session.localized.ko || !session.localized.en) errors.push(`LIVE_LOCALE_MISSING:${session.id}`)
    if (!session.provenance?.referenceId) errors.push(`LIVE_PROVENANCE_MISSING:${session.id}`)
    session.placeIds.forEach((id) => !ids.place.has(id) && errors.push(`LIVE_PLACE_FK_BROKEN:${session.id}:${id}`))
    session.articleIds.forEach((id) => !ids.article.has(id) && errors.push(`LIVE_ARTICLE_FK_BROKEN:${session.id}:${id}`))
  }

  return errors.length === 0 ? { ok: true, releaseId: manifest.releaseId } : { ok: false, errors }
}
