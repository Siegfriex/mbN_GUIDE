import { useEffect, useState } from 'react'
import type { Place, PlaceCategory } from '../../entities/place'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { FIXTURE_RELEASE } from '../../app/config'
import { useI18n } from '../../shared/i18n'
import { EmptyState, Skeleton, StatusNotice } from '../../shared/ui'
import { navigate, createPlacePath } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'
import { MapDiscoveryWorkspace } from '../../widgets/map-discovery-workspace'

export function GuidePage() {
  const [selectedCategory, setSelectedCategory] = useState<PlaceCategory | 'all'>('all')
  const [result, setResult] = useState<{ category: PlaceCategory | 'all'; places: Place[] } | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const { locale } = useI18n()

  useEffect(() => {
    let isCurrent = true
    fixtureProjection
      .listPlaces(selectedCategory)
      .then((places) => {
        if (isCurrent) {
          setResult({ category: selectedCategory, places })
          setError(null)
          track('guide_viewed', { locale, source: 'fixture', category: selectedCategory })
        }
      })
      .catch((nextError: Error) => isCurrent && setError(nextError))
    return () => {
      isCurrent = false
    }
  }, [locale, selectedCategory])

  const handleSelectCategory = (category: PlaceCategory | 'all') => {
    setSelectedCategory(category)
    track('guide_filter_changed', { category, source: 'fixture' })
  }

  const places = result?.category === selectedCategory ? result.places : null

  return (
    <>
      <main className="product-page">
        <StatusNotice state="UNAVAILABLE" title="Demo release — not empirical data">
          {FIXTURE_RELEASE.releaseId} · Data contract {FIXTURE_RELEASE.contractVersions.data} · No PY release is consumed.
        </StatusNotice>
        {error && result?.category !== selectedCategory ? <EmptyState title="Fixture loading failed." description={error.message} /> : null}
        {places === null && !error ? <Skeleton className="guide-skeleton" /> : null}
        {places ? (
          <MapDiscoveryWorkspace
            places={places}
            locale={locale}
            selectedCategory={selectedCategory}
            onSelectCategory={handleSelectCategory}
            onOpenPlace={(place) => {
              track('map_pin_opened', { placeId: place.id, category: place.category, provenance: place.provenance.source })
              navigate(createPlacePath(place.id))
            }}
          />
        ) : null}
      </main>
      <PrimaryNavigation />
    </>
  )
}
