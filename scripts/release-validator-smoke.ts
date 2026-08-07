import { createHash } from 'node:crypto'
import { REQUIRED_RELEASE_FILE_PATHS, validateReleaseBundle } from '../src/app/release/releaseValidator'
import type { ReleaseBundle } from '../src/app/release/types'

const encoder = new TextEncoder()
const bytes = encoder.encode('{"fixture":true}')
const sha = createHash('sha256').update(bytes).digest('hex')
const localized = { ko: { name: '데모', summary: '데모', whyItMatters: '데모', availableExperience: '데모' }, en: { name: 'Demo', summary: 'Demo', whyItMatters: 'Demo', availableExperience: 'Demo' } }
const provenance = { source: 'editor' as const, referenceId: 'fixture:test', label: { ko: '데모', en: 'Demo' }, method: 'fixture' as const, isSponsored: false }

function makeBundle(): ReleaseBundle {
  const files = Object.fromEntries(REQUIRED_RELEASE_FILE_PATHS.map((path) => [path, bytes]))
  return {
    manifest: { releaseId: 'VALID_TEST_RELEASE', sourceRepository: 'test', sourceBranch: 'test', sourceCommit: 'test', contractVersion: '0.3.0', schemaVersion: '0.3.0', taxonomyVersion: '0.3.0', pipelineVersion: 'test', generatedAt: '2026-08-07T00:00:00.000Z', qualityStatus: 'PASS', files: REQUIRED_RELEASE_FILE_PATHS.map((path) => ({ path, sha256: sha, required: true })) },
    files,
    projection: {
      places: [{ id: 'p1', slug: 'p1', coordinates: { lat: 0, lng: 0 }, address: { ko: '데모', en: 'Demo' }, category: 'music', tags: [], localized, localeSupport: ['ko', 'en'], source: 'editor', provenance, relatedStoryIds: ['s1'], relatedLiveIds: ['l1'], offerIds: [], status: 'active' }],
      articles: [{ id: 'a1', sourceArticleId: 'source:a1', source: 'editor', rawTitle: 'Demo', cleanTitle: 'Demo', localized: { ko: { headline: '데모', excerpt: '데모' }, en: { headline: 'Demo', excerpt: 'Demo' } }, category: 'music', tags: [], placeIds: ['p1'], storyIds: ['s1'], status: 'active', provenance: { ...provenance, referenceId: 'fixture:article' } }],
      stories: [{ id: 's1', localized: { ko: { headline: '데모', deck: '데모', summary: '데모' }, en: { headline: 'Demo', deck: 'Demo', summary: 'Demo' } }, articleIds: ['a1'], placeIds: ['p1'], liveIds: ['l1'], tags: [], provenance: { ...provenance, referenceId: 'fixture:story' }, status: 'active' }],
      liveSessions: [{ id: 'l1', lifecycle: 'replay', category: 'music', localized: { ko: { title: '데모', deck: '데모', summary: '데모' }, en: { title: 'Demo', deck: 'Demo', summary: 'Demo' } }, hostName: 'Demo', player: { status: 'unavailable' }, chat: { status: 'unavailable' }, offer: { status: 'unavailable' }, placeIds: ['p1'], articleIds: ['a1'], offerIds: [], provenance: { ...provenance, referenceId: 'fixture:live' } }],
    },
  }
}

async function expectInvalid(mutator: (bundle: ReleaseBundle) => void, expectedError: string) {
  const bundle = makeBundle()
  mutator(bundle)
  const result = await validateReleaseBundle(bundle)
  if (result.ok || !result.errors.includes(expectedError)) throw new Error(`Expected ${expectedError}, got ${JSON.stringify(result)}`)
}

const valid = await validateReleaseBundle(makeBundle())
if (!valid.ok) throw new Error(`Valid release rejected: ${JSON.stringify(valid)}`)
await expectInvalid((bundle) => { bundle.manifest.qualityStatus = 'FAIL' }, 'MANIFEST_QUALITY_NOT_PASS')
await expectInvalid((bundle) => { bundle.manifest.contractVersion = 'bad' }, 'CONTRACT_VERSION_MISMATCH')
await expectInvalid((bundle) => { bundle.files['places.json'] = encoder.encode('tampered') }, 'FILE_SHA_MISMATCH:places.json')
await expectInvalid((bundle) => { delete bundle.files['places.json'] }, 'DECLARED_FILE_MISSING:places.json')
await expectInvalid((bundle) => { bundle.manifest.files = bundle.manifest.files.filter((file) => file.path !== 'offers.json') }, 'REQUIRED_FILE_UNDECLARED:offers.json')
await expectInvalid((bundle) => { bundle.projection.places[0]!.relatedStoryIds = ['missing'] }, 'PLACE_STORY_FK_BROKEN:p1:missing')
await expectInvalid((bundle) => { delete bundle.projection.places[0]!.localized.en }, 'PLACE_LOCALE_MISSING:p1')
await expectInvalid((bundle) => { bundle.projection.places[0]!.provenance.referenceId = '' }, 'PLACE_PROVENANCE_MISSING:p1')
console.log('Release validator smoke passed: valid + 8 fail-closed cases.')
