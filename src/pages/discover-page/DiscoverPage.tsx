import { useEffect, useState } from 'react'
import type { Story } from '../../entities/story'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, EmptyState, Skeleton, StatusNotice } from '../../shared/ui'
import { navigate } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'
import { MagazineFeed } from '../../widgets/magazine-feed'

type DiscoverView = 'magazine' | 'community'

export function DiscoverPage() {
  const initialView: DiscoverView = new URLSearchParams(window.location.search).get('view') === 'community' ? 'community' : 'magazine'
  const [view, setView] = useState<DiscoverView>(initialView)
  const [stories, setStories] = useState<Story[] | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const { locale } = useI18n()

  useEffect(() => {
    let isCurrent = true
    fixtureProjection.listStories()
      .then((result) => {
        if (isCurrent) {
          setStories(result)
          setError(null)
          track('discover_viewed', { view, source: 'fixture' })
        }
      })
      .catch((nextError: Error) => isCurrent && setError(nextError))
    return () => { isCurrent = false }
  }, [view])

    const changeView = (nextView: DiscoverView) => {
    setView(nextView)
    window.history.replaceState(null, '', `/discover?view=${nextView}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
    track('discover_view_changed', { view: nextView })
    if (nextView === 'community') track('community_opened', { mode: 'unavailable', source: 'fixture' })
  }

  return (
    <>
      <main className="product-page">
        <header className="surface-header"><p className="eyebrow">DISCOVER</p><h1>Editorial context</h1><p>Fixture-only content. Community is governed as unavailable until an approved projection exists.</p></header>
        <div className="segmented-control" role="tablist" aria-label="Discover view">
          <Button variant={view === 'magazine' ? 'primary' : 'secondary'} onClick={() => changeView('magazine')} role="tab" aria-selected={view === 'magazine'}>Magazine</Button>
          <Button variant={view === 'community' ? 'primary' : 'secondary'} onClick={() => changeView('community')} role="tab" aria-selected={view === 'community'}>Community</Button>
        </div>
        {view === 'magazine' && stories === null && !error ? <Skeleton className="guide-skeleton" /> : null}
        {view === 'magazine' && error ? <StatusNotice state="ERROR" title="Editorial fixture loading failed">{error.message}</StatusNotice> : null}
        {view === 'magazine' && stories ? <MagazineFeed stories={stories} locale={locale} onOpenStory={(story) => navigate(`/story/${encodeURIComponent(story.id)}`)} /> : null}
        {view === 'community' ? <><StatusNotice state="UNAVAILABLE" title="Community projection unavailable">No writable feed, participant identity, activity count, or moderation status is simulated.</StatusNotice><EmptyState title="No governed CommunityPost fixture" description="This is not shown as a successful social feed." /></> : null}
      </main>
      <PrimaryNavigation />
    </>
  )
}
