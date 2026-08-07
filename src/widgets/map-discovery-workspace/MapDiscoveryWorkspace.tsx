import type { Place, PlaceCategory } from '../../entities/place'
import { getPlaceContent } from '../../entities/place'
import { useI18n } from '../../shared/i18n'
import type { Locale } from '../../shared/i18n'
import { Button, EmptyState, StatusNotice } from '../../shared/ui'

type MapDiscoveryWorkspaceProps = {
  places: Place[]
  locale: Locale
  selectedCategory: PlaceCategory | 'all'
  onSelectCategory: (category: PlaceCategory | 'all') => void
  onOpenPlace: (place: Place) => void
}

const categoryOrder: Array<PlaceCategory | 'all'> = [
  'all',
  'performance',
  'exhibition',
  'music',
  'food',
  'beauty-fashion',
  'broadcast-media',
  'healing',
  'activity',
]

export function MapDiscoveryWorkspace({
  places,
  locale,
  selectedCategory,
  onSelectCategory,
  onOpenPlace,
}: MapDiscoveryWorkspaceProps) {
  const { t } = useI18n()
  return (
    <section className="discovery-workspace" aria-labelledby="discovery-workspace-title">
      <header className="discovery-workspace__header">
        <p className="eyebrow">GUIDE</p>
        <h1 id="discovery-workspace-title">{t('guide.title')}</h1>
        <p>{t('guide.description')}</p>
      </header>

      <StatusNotice state="UNAVAILABLE" title={t('guide.mapUnavailableTitle')}>
        {t('guide.mapUnavailableDescription')}
      </StatusNotice>

      <div className="filter-row" aria-label={t('guide.filters')}>
        {categoryOrder.map((category) => (
          <button
            key={category}
            className={selectedCategory === category ? 'filter-chip filter-chip--active' : 'filter-chip'}
            aria-pressed={selectedCategory === category}
            onClick={() => onSelectCategory(category)}
          >
            {category === 'all' ? t('guide.all') : category}
          </button>
        ))}
      </div>

      {places.length === 0 ? (
        <EmptyState title={t('guide.noMatches')} description={t('guide.noMatchesDescription')} />
      ) : (
        <div className="discovery-tray">
          {places.map((place) => {
            const content = getPlaceContent(place, locale)
            return (
              <article className="place-preview" key={place.id}>
                <div className="place-preview__meta">
                  <span>{place.category}</span>
                  <span>{place.status === 'active' ? t('guide.fixtureActive') : t('guide.unavailable')}</span>
                </div>
                <h2>{content.name}</h2>
                <p>{content.summary}</p>
                <p className="place-preview__why"><strong>{t('guide.whyItMatters')}</strong> {content.whyItMatters}</p>
                <p className="place-preview__provenance">{place.provenance.label[locale]}</p>
                <Button variant="secondary" onClick={() => onOpenPlace(place)}>{t('common.openDetail')}</Button>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
