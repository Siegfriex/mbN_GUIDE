import type { Story } from '../../entities/story'
import { getStoryContent } from '../../entities/story'
import { useI18n } from '../../shared/i18n'
import type { Locale } from '../../shared/i18n'
import { Button, EmptyState } from '../../shared/ui'

type MagazineFeedProps = {
  stories: Story[]
  locale: Locale
  onOpenStory: (story: Story) => void
}

export function MagazineFeed({ stories, locale, onOpenStory }: MagazineFeedProps) {
  const { t } = useI18n()
  if (stories.length === 0) {
    return <EmptyState title={t('discover.noStoriesTitle')} description={t('discover.noStoriesDescription')} />
  }

  return (
    <section className="editorial-feed" aria-label={t('discover.magazine')}>
      {stories.map((story) => {
        const content = getStoryContent(story, locale)
        return (
          <article className="editorial-card" key={story.id}>
            <p className="eyebrow">{content.deck}</p>
            <h2>{content.headline}</h2>
            <p>{content.summary}</p>
            <p className="place-preview__provenance">{story.provenance.label[locale]}</p>
            <Button onClick={() => onOpenStory(story)}>{t('common.openStory')}</Button>
          </article>
        )
      })}
    </section>
  )
}
