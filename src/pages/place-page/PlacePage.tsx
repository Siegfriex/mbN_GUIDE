import { useEffect, useState } from 'react'
import type { Place } from '../../entities/place'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, EmptyState, Skeleton } from '../../shared/ui'
import { navigate } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'
import { PlaceDetailContent } from '../../widgets/place-detail-sheet'

type PlacePageProps = {
  placeId: string
}

export function PlacePage({ placeId }: PlacePageProps) {
  const [place, setPlace] = useState<Place | null | undefined>(undefined)
  const { locale, t } = useI18n()

  useEffect(() => {
    let isCurrent = true
    fixtureProjection.getPlace(placeId).then((result) => {
      if (isCurrent) {
        setPlace(result)
        if (result) {
          track('place_detail_viewed', { placeId: result.id, entryPoint: 'guide' })
        }
      }
    })
    return () => {
      isCurrent = false
    }
  }, [placeId])

  return (
    <>
      <main className="product-page">
        <Button variant="ghost" onClick={() => navigate('/guide')}>{t('place.back')}</Button>
        {place === undefined ? <Skeleton className="guide-skeleton" /> : null}
        {place === null ? <EmptyState title={t('guide.unavailable')} description="The requested fixture ID does not exist." /> : null}
        {place ? <PlaceDetailContent place={place} locale={locale} /> : null}
      </main>
      <PrimaryNavigation />
    </>
  )
}
