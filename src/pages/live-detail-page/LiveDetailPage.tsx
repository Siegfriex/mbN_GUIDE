import { useEffect, useState } from 'react'
import type { LiveSession } from '../../entities/live-session'
import { getLiveContent } from '../../entities/live-session'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, Card, EmptyState, Skeleton, StatusNotice } from '../../shared/ui'
import { navigate, createPlacePath } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'

type LiveDetailPageProps = { sessionId: string }

export function LiveDetailPage({ sessionId }: LiveDetailPageProps) {
  const [session, setSession] = useState<LiveSession | null | undefined>(undefined)
  const { locale, t } = useI18n()
  useEffect(() => { let isCurrent = true; fixtureProjection.getLiveSession(sessionId).then((result) => { if (isCurrent) { setSession(result); if (result) { track('live_session_opened', { sessionId: result.id, status: result.lifecycle }); track('live_status_viewed', { sessionId: result.id, lifecycle: result.lifecycle, playerStatus: result.player.status }); track('chat_shell_viewed', { sessionId: result.id, chatStatus: result.chat.status }) } } }); return () => { isCurrent = false } }, [sessionId])
  const content = session ? getLiveContent(session, locale) : null
  return <><main className="product-page"><Button variant="ghost" onClick={() => navigate('/live')}>{t('live.back')}</Button>{session === undefined ? <Skeleton className="guide-skeleton" /> : null}{session === null ? <EmptyState title={t('live.unavailable')} /> : null}{session && content ? <article className="place-detail"><header className="place-detail__header"><p className="eyebrow">{session.lifecycle.toUpperCase()}</p><h1>{content.title}</h1><p>{content.summary}</p><p className="place-preview__provenance">{session.provenance.label[locale]}</p></header><Card><h2>{t('live.player')}</h2><StatusNotice state={session.player.status === 'available' ? 'SUCCESS' : 'UNAVAILABLE'} title={session.player.status === 'available' ? t('live.playerAvailable') : t('live.playerUnavailable')}>{session.player.status === 'available' ? 'A provider-backed player would render here.' : t('live.playerUnavailableDescription')}</StatusNotice></Card><Card><h2>{t('live.chat')}</h2><StatusNotice state={session.chat.status === 'available' ? 'SUCCESS' : 'UNAVAILABLE'} title={session.chat.status === 'available' ? t('live.chatAvailable') : t('live.chatUnavailable')}>{session.chat.status === 'available' ? 'Provider-backed chat is available.' : t('live.chatUnavailableDescription')}</StatusNotice></Card><Card><h2>{t('live.relatedPlace')}</h2>{session.placeIds.length ? session.placeIds.map((placeId) => <Button key={placeId} variant="secondary" onClick={() => navigate(createPlacePath(placeId))}>{t('common.openPlace')}</Button>) : <EmptyState title={t('live.noRelatedPlace')} />}</Card><Card><h2>{t('live.offer')}</h2><StatusNotice state={session.offer.status === 'available' ? 'SUCCESS' : 'UNAVAILABLE'} title={session.offer.status === 'available' ? t('live.playerAvailable') : t('live.noOffer')}>{session.offer.status === 'available' ? 'Offer projection is eligible for a separate CTA adapter.' : t('live.noOfferDescription')}</StatusNotice></Card></article> : null}</main><PrimaryNavigation /></>
}
