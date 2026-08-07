import type { Article } from '../../entities/article'
import type { LiveSession } from '../../entities/live-session'
import type { Place } from '../../entities/place'
import type { Story } from '../../entities/story'

export type ReleaseQualityStatus = 'PASS' | 'FAIL'

export type FrontendReleaseManifest = {
  releaseId: string
  sourceRepository: string
  sourceBranch: string
  sourceCommit: string
  contractVersion: string
  schemaVersion: string
  taxonomyVersion: string
  pipelineVersion: string
  generatedAt: string
  qualityStatus: ReleaseQualityStatus
  files: Array<{ path: string; sha256: string; required: boolean }>
}

export type ReleaseProjection = {
  places: Place[]
  articles: Article[]
  stories: Story[]
  liveSessions: LiveSession[]
}

export type ReleaseBundle = {
  manifest: FrontendReleaseManifest
  files: Record<string, Uint8Array>
  projection: ReleaseProjection
}

export type ReleaseValidationResult =
  | { ok: true; releaseId: string }
  | { ok: false; errors: string[] }
