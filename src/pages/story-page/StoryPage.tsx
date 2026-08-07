import { createPlacePath, navigate, safeReturnPath } from '../../app/router/navigation'
import { getArticleContent } from '../../entities/article'
import { getLiveContent } from '../../entities/live-session'
import { useStoryPageModel } from '../../features/projection-query'
import { SaveItemButton } from '../../features/save-item'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, ContextRelationCard, EmptyState, MediaFrame, Skeleton, StatusNotice, SurfaceSection } from '../../shared/ui'
import '../../widgets/story-detail-surface/editorial-detail.css'

type StoryPageProps = { storyId: string }

export function StoryPage({ storyId }: StoryPageProps) {
  const { locale, t } = useI18n()
  const storyModel = useStoryPageModel(storyId, locale)
  const { story, resolution } = storyModel
  const returnTo = safeReturnPath(new URLSearchParams(window.location.search).get('returnTo'), '/discover?view=magazine')

  return <main id="main-content" className="product-page editorial-detail-page figma-detail-page">
    <header className="figma-detail-page__topbar"><Button variant="ghost" className="figma-detail-page__back" onClick={() => navigate(returnTo)} aria-label={t('story.back')}>‹</Button><p>매거진 · 문화</p></header>
    {storyModel.data === undefined && !storyModel.error ? <Skeleton className="guide-skeleton" /> : null}
    {storyModel.error ? <StatusNotice state="ERROR" title={t('state.errorTitle')}>{storyModel.error.message}<Button onClick={storyModel.reload}>{t('common.retry')}</Button></StatusNotice> : null}
    {storyModel.data && !story ? <EmptyState title={t('story.unavailable')} description={t('state.unknownStory')} /> : null}
    {story && resolution ? <article className="editorial-detail" aria-labelledby="story-detail-title">
      <MediaFrame className="editorial-detail__hero" label={t('story.videoUnavailableTitle')} eyebrow={t('story.video')}>
        <span className="editorial-detail__media-note">{t('story.videoUnavailableDescription')}</span>
      </MediaFrame>
      <header className="editorial-detail__header">
        <div className="editorial-detail__tags"><span>{resolution.content.deck}</span><span>fixture</span></div>
        <h1 id="story-detail-title">{resolution.content.headline}</h1>
        <p className="editorial-detail__provenance">{story.provenance.label[locale]}</p>
        <p className="editorial-detail__summary">{resolution.content.summary}</p>
      </header>
      {resolution.fallbackUsed ? <StatusNotice state="UNAVAILABLE" title={t('locale.fallbackTitle')}>{t('locale.fallbackDescription')}</StatusNotice> : null}
      <SurfaceSection title={t('story.articleContext')} className="editorial-detail__section">
        {storyModel.articles.length ? storyModel.articles.map((article) => <ContextRelationCard key={article.id} label={t('story.articleContext')} title={getArticleContent(article, locale).headline} description={getArticleContent(article, locale).excerpt} provenance={article.provenance.label[locale]} />) : <EmptyState title={t('story.noArticle')} />}
      </SurfaceSection>
      <SurfaceSection title={t('story.relatedPlaces')} className="editorial-detail__section">
        {story.placeIds.length ? story.placeIds.map((placeId) => <Button key={placeId} variant="secondary" onClick={() => { track('related_place_opened', { originType: 'story', originId: story.id, placeId }); navigate(createPlacePath(placeId, returnTo)) }}>{t('common.openPlace')}</Button>) : <EmptyState title={t('story.noRelatedPlace')} />}
      </SurfaceSection>
      <SurfaceSection title={t('story.relatedLive')} className="editorial-detail__section">
        {storyModel.lives.length ? storyModel.lives.map((session) => <Button key={session.id} variant="secondary" onClick={() => navigate(`/live/${encodeURIComponent(session.id)}?returnTo=${encodeURIComponent(returnTo)}`)}>{getLiveContent(session, locale).title}</Button>) : <EmptyState title={t('live.noSessionsTitle')} />}
      </SurfaceSection>
      <section className="editorial-detail__actions" aria-label={t('place.actions')}><SaveItemButton targetType="story" targetId={story.id} /></section>
    </article> : null}
  </main>
}
