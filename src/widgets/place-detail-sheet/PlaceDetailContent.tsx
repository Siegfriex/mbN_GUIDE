import type { Place } from '../../entities/place'
import { getPlaceContent } from '../../entities/place'
import { SavePlaceButton } from '../../features/save-item'
import { SharePlaceButton } from '../../features/share-item'
import type { Locale } from '../../shared/i18n'
import { useI18n } from '../../shared/i18n'
import { Card, EmptyState, StatusNotice } from '../../shared/ui'

type PlaceDetailContentProps = {
  place: Place
  locale: Locale
}

export function PlaceDetailContent({ place, locale }: PlaceDetailContentProps) {
  const content = getPlaceContent(place, locale)
  const { t } = useI18n()

  return (
    <article className="place-detail" aria-labelledby="place-detail-title">
      <header className="place-detail__header">
        <p className="eyebrow">{place.category}</p>
        <h1 id="place-detail-title">{content.name}</h1>
        <p>{content.summary}</p>
        <p className="place-preview__provenance">{place.provenance.label[locale]}</p>
      </header>

      {place.status === 'unavailable' ? (
        <StatusNotice state="UNAVAILABLE" title="Current availability is not verified.">
          This known fixture remains visible, but it is not actionable.
        </StatusNotice>
      ) : null}

      <Card>
        <h2>{t('place.why')}</h2>
        <p>{content.whyItMatters}</p>
      </Card>
      <Card>
        <h2>{t('place.experience')}</h2>
        <p>{content.availableExperience}</p>
      </Card>
      <Card>
        <h2>{t('place.editorial')}</h2>
        <EmptyState title={t('place.noStoryTitle')} description={t('place.noStoryDescription')} />
      </Card>
      <Card>
        <h2>{t('place.community')}</h2>
        <EmptyState title={t('place.communityTitle')} description={t('place.communityDescription')} />
      </Card>
      <section className="place-detail__actions" aria-label={t('place.actions')}>
        <SavePlaceButton placeId={place.id} />
        <SharePlaceButton placeId={place.id} title={content.name} description={content.summary} />
      </section>
      <Card>
        <h2>{t('place.offer')}</h2>
        <StatusNotice state="UNAVAILABLE" title={t('place.offerTitle')}>
          {t('place.offerDescription')}
        </StatusNotice>
      </Card>
    </article>
  )
}
