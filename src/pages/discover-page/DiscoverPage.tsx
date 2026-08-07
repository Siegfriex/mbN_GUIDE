import { useState } from 'react'
import { navigate } from '../../app/router/navigation'
import { useStoryCollection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, EmptyState, SegmentedControl, Skeleton, StatusNotice } from '../../shared/ui'
import { MagazineFeed } from '../../widgets/magazine-feed'

type DiscoverView = 'magazine' | 'community'

function readDiscoverState() {
  const query = new URLSearchParams(window.location.search)
  return {
    view: query.get('view') === 'community' ? 'community' as const : 'magazine' as const,
    theme: query.get('theme') ?? 'all',
  }
}

export function DiscoverPage() {
  const [initial] = useState(readDiscoverState)
  const [view, setView] = useState<DiscoverView>(initial.view)
  const [searchQuery, setSearchQuery] = useState('')
  const { locale, t } = useI18n()
  const { data: stories, error, reload } = useStoryCollection(view)

  const updateRoute = (nextView: DiscoverView) => {
    const query = new URLSearchParams({ view: nextView })
    navigate(`/discover?${query.toString()}`, { replace: true })
  }

  const changeView = (next: DiscoverView) => {
    setView(next)
    updateRoute(next)
    track('discover_view_changed', { view: next })
    if (next === 'community') track('community_opened', { mode: 'unavailable', source: 'fixture' })
  }

  return (
    <main id="main-content" className="figma-mobile-page magazine-home">
      <header className="figma-topbar" aria-label="매거진 도구">
        <form className="figma-search" onSubmit={(event) => { event.preventDefault(); navigate(`/search?q=${encodeURIComponent(searchQuery)}`) }}>
          <label className="visually-hidden" htmlFor="magazine-search">매거진 검색</label>
          <input id="magazine-search" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="매거진 검색" />
          <Button type="submit" className="figma-search__submit">검색</Button>
        </form>
        <Button variant="secondary" className="figma-topbar__utility" aria-label={t('nav.settings')} onClick={() => navigate('/settings')}>설정</Button>
      </header>
      <h1 className="visually-hidden">{t('discover.title')}</h1>
      <div className="magazine-home__view-switch">
        <SegmentedControl
          label={t('discover.view')}
          value={view}
          options={[{ value: 'magazine', label: t('discover.magazine') }, { value: 'community', label: t('discover.community') }]}
          onChange={changeView}
        />
      </div>

      {view === 'magazine' ? (
        <>
          {stories === null && !error ? <Skeleton className="guide-skeleton" /> : null}
          {error ? <StatusNotice state="ERROR" title={t('state.errorTitle')}>{error.message}<Button onClick={reload}>{t('common.retry')}</Button></StatusNotice> : null}
          {stories ? <MagazineFeed stories={stories} locale={locale} onOpenStory={(story) => navigate(`/story/${encodeURIComponent(story.id)}?returnTo=${encodeURIComponent(window.location.pathname + window.location.search)}`)} /> : null}
          {stories?.length === 0 ? <EmptyState title={t('discover.noStoriesTitle')} description={t('discover.noStoriesDescription')} /> : null}
          <section className="magazine-home__notice" aria-labelledby="magazine-notice-title">
            <div className="magazine-home__section-title"><h2 id="magazine-notice-title">공지사항</h2></div>
            <button type="button" onClick={() => navigate('/settings')}>표시 언어 지원 확대 안내<span aria-hidden="true">›</span></button>
            <button type="button" onClick={() => changeView('community')}>게시 공간 공개 상태 안내<span aria-hidden="true">›</span></button>
          </section>
        </>
      ) : (
        <section className="discover-community-state">
          <StatusNotice state="UNAVAILABLE" title={t('discover.communityUnavailableTitle')}>{t('discover.communityUnavailableDescription')}</StatusNotice>
          <EmptyState title={t('discover.noCommunityTitle')} description={t('discover.noCommunityDescription')} />
        </section>
      )}
    </main>
  )
}
