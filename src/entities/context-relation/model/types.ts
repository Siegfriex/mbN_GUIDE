export type FixtureRelationProvenance = {
  source: 'FRONT_FIXTURE'
  nonEmpirical: true
  declaredBy: 'manual-fixture'
}

export type RelatedArticle = {
  articleId: string
  relationType: 'article-place' | 'article-article'
  evidence: string
  provenance: FixtureRelationProvenance
}

export type RelatedLive = {
  liveSessionId: string
  relationType: 'article-live' | 'place-live'
  disclosureEligible: boolean
  evidence: string
  provenance: FixtureRelationProvenance
}
