import type { Story } from '../../entities/story'
import { toStoryViewModel } from '../../features/projection-query'
import { useI18n } from '../../shared/i18n'
import type { Locale } from '../../shared/i18n'
import { Button, EmptyState } from '../../shared/ui'
import './discover.css'

type MagazineFeedProps = {
  stories: Story[]
  locale: Locale
  onOpenStory: (story: Story) => void
}

export function MagazineFeed({ stories, locale, onOpenStory }: MagazineFeedProps) {
  const { t } = useI18n()
  if (stories.length === 0) return <EmptyState title={t('discover.noStoriesTitle')} description={t('discover.noStoriesDescription')} />

  const featured = stories[0]!
  const featuredViewModel = toStoryViewModel(featured, locale)

  return (
    <div className="magazine-feed">
      <section className="magazine-feed__section" aria-labelledby="hot-magazine-title">
        <header className="magazine-feed__heading"><p aria-hidden="true">♨</p><h2 id="hot-magazine-title">HOT 매거진</h2></header>
        <div className="magazine-card-rail" aria-label={t('discover.featured')}>
          <article className="magazine-card magazine-card--featured">
            <div className="magazine-card__image" aria-label={t('discover.storyMedia')}><span>승인된 미디어 없음</span></div>
            <div className="magazine-card__body">
              <p className="magazine-card__tag">{featuredViewModel.deck}</p>
              <h3>{featuredViewModel.headline}</h3>
              <p className="magazine-card__provenance">{featuredViewModel.provenanceLabel}</p>
              <Button size="sm" variant="ghost" onClick={() => onOpenStory(featured)}>{t('common.openStory')}</Button>
            </div>
          </article>
        </div>
      </section>
      {stories.slice(1).length ? <section className="magazine-feed__section" aria-labelledby="all-magazine-title">
        <header className="magazine-feed__heading"><h2 id="all-magazine-title">{t('discover.stream')}</h2></header>
        <div className="magazine-card-rail" aria-label={t('discover.stream')}>
          {stories.slice(1).map((story) => {
            const viewModel = toStoryViewModel(story, locale)
            return (
              <article className="magazine-card" key={story.id}>
                <div className="magazine-card__image" aria-label={t('discover.storyMedia')}><span>승인된 미디어 없음</span></div>
                <div className="magazine-card__body">
                  <p className="magazine-card__tag">{viewModel.deck}</p>
                  <h3>{viewModel.headline}</h3>
                  <p className="magazine-card__provenance">{viewModel.provenanceLabel}</p>
                  <Button size="sm" variant="ghost" onClick={() => onOpenStory(story)}>{t('common.openStory')}</Button>
                </div>
              </article>
            )
          })}
        </div>
      </section> : null}
    </div>
  )
}
