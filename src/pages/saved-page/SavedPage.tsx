import { useEffect, useState } from 'react'
import type { Place } from '../../entities/place'
import { getPlaceContent } from '../../entities/place'
import { fixtureProjection } from '../../features/projection-query'
import { getSavedItems } from '../../features/save-item'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, EmptyState, Skeleton, StatusNotice } from '../../shared/ui'
import { createPlacePath, navigate } from '../../app/router/navigation'
import { PrimaryNavigation, UtilityNavigation } from '../../widgets/app-chrome'

export function SavedPage() {
  const [places, setPlaces] = useState<Place[] | null>(null)
  const { locale } = useI18n()

  useEffect(() => {
    let isCurrent = true
    const saved = getSavedItems()
    Promise.all(saved.map((item) => fixtureProjection.getPlace(item.targetId))).then((results) => {
      if (isCurrent) {
        setPlaces(results.filter((place): place is Place => place !== null))
        track('saved_hub_viewed', { collection: 'default', itemCount: saved.length })
      }
    })
    return () => { isCurrent = false }
  }, [])

  return <><main className="product-page"><UtilityNavigation /><header className="surface-header"><p className="eyebrow">SAVED</p><h1>Saved references</h1><p>Saved data stores only fixture target IDs on this device; it does not create a source snapshot.</p></header>{places === null ? <Skeleton className="guide-skeleton" /> : null}{places?.length === 0 ? <EmptyState title="No saved fixtures" description="Save a fixture Place from its detail page to see it here." /> : null}{places?.map((place) => <article className="place-preview" key={place.id}><h2>{getPlaceContent(place, locale).name}</h2><p>{getPlaceContent(place, locale).summary}</p>{place.status === 'unavailable' ? <StatusNotice state="UNAVAILABLE" title="Target unavailable">The saved reference is retained for auditability.</StatusNotice> : null}<Button variant="secondary" onClick={() => navigate(createPlacePath(place.id))}>Open saved item</Button></article>)}</main><PrimaryNavigation /></>
}
