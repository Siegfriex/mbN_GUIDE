import { useEffect, useState } from 'react'
import type { Story } from '../../entities/story'
import { getStoryContent } from '../../entities/story'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, Card, EmptyState, Skeleton, StatusNotice } from '../../shared/ui'
import { navigate, createPlacePath } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'

type StoryPageProps = { storyId: string }

export function StoryPage({ storyId }: StoryPageProps) {
  const [story, setStory] = useState<Story | null | undefined>(undefined)
  const { locale, t } = useI18n()

  useEffect(() => {
    let isCurrent = true
    fixtureProjection.getStory(storyId).then((result) => {
      if (isCurrent) {
        setStory(result)
        if (result) track('story_opened', { storyId: result.id, source: result.provenance.source })
      }
    })
    return () => { isCurrent = false }
  }, [storyId])

  const content = story ? getStoryContent(story, locale) : null
  return <><main className="product-page"><Button variant="ghost" onClick={() => navigate('/discover')}>{t('story.back')}</Button>{story === undefined ? <Skeleton className="guide-skeleton" /> : null}{story === null ? <EmptyState title={t('story.unavailable')} /> : null}{story && content ? <article className="place-detail"><header className="place-detail__header"><p className="eyebrow">{content.deck}</p><h1>{content.headline}</h1><p>{content.summary}</p><p className="place-preview__provenance">{story.provenance.label[locale]}</p></header><Card><h2>{t('story.video')}</h2><StatusNotice state="UNAVAILABLE" title={t('story.videoUnavailableTitle')}>{t('story.videoUnavailableDescription')}</StatusNotice></Card><Card><h2>{t('story.relatedPlaces')}</h2>{story.placeIds.length ? story.placeIds.map((placeId) => <Button key={placeId} variant="secondary" onClick={() => { track('related_place_opened', { originType: 'story', originId: story.id, placeId }); navigate(createPlacePath(placeId)) }}>{t('common.openPlace')}</Button>) : <EmptyState title={t('story.noRelatedPlace')} />}</Card></article> : null}</main><PrimaryNavigation /></>
}
