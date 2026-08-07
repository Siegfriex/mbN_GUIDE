import { useState } from 'react'
import type { PlaceCategory } from '../../entities/place'
import { PLACE_CATEGORIES } from '../../entities/place'
import type { TravelerProfile, VisitorMode } from '../../entities/traveler-profile'
import { getTravelerProfile, setTravelerProfile } from '../../features/manage-traveler-profile'
import { track } from '../../shared/analytics'
import type { AnalyticsEventName } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { StatusNotice, useToast } from '../../shared/ui'
import { PrimaryNavigation, UtilityNavigation } from '../../widgets/app-chrome'

export function SettingsPage() {
  const { locale, setLocale } = useI18n()
  const [profile, setProfile] = useState<TravelerProfile>(() => getTravelerProfile())
  const { pushToast } = useToast()

  const updateProfile = (next: TravelerProfile, eventName: Extract<AnalyticsEventName, 'locale_changed' | 'visitor_mode_updated' | 'interests_updated'>) => {
    const persistenceStatus: TravelerProfile['persistenceStatus'] = setTravelerProfile(next) ? 'local' : 'unavailable'
    const persisted = { ...next, persistenceStatus }
    setProfile(persisted)
    track(eventName, { persistenceStatus })
    pushToast({ message: persistenceStatus === 'local' ? 'Saved on this device.' : 'Device storage is unavailable.' })
  }

  const updateLocale = (nextLocale: string) => {
    setLocale(nextLocale)
    updateProfile({ ...profile, locale: nextLocale === 'en' ? 'en' : 'ko' }, 'locale_changed')
  }

  const toggleInterest = (interest: PlaceCategory) => {
    const interests = profile.interests.includes(interest) ? profile.interests.filter((item) => item !== interest) : [...profile.interests, interest]
    updateProfile({ ...profile, interests }, 'interests_updated')
  }

  return <><main className="product-page"><UtilityNavigation /><header className="surface-header"><p className="eyebrow">SETTINGS</p><h1>Local preferences</h1><p>Preferences remain on this device. They do not change a recommendation model in this fixture build.</p></header><label className="locale-control"><span>Language</span><select value={locale} onChange={(event) => updateLocale(event.target.value)}><option value="ko">한국어</option><option value="en">English</option></select></label><fieldset className="settings-fieldset"><legend>Visitor mode</legend>{(['foreigner', 'domestic-traveler', 'local-explorer'] as VisitorMode[]).map((mode) => <label key={mode}><input type="radio" name="visitor-mode" checked={profile.visitorMode === mode} onChange={() => updateProfile({ ...profile, visitorMode: mode }, 'visitor_mode_updated')} /> {mode}</label>)}</fieldset><fieldset className="settings-fieldset"><legend>Interests</legend><div className="filter-row">{PLACE_CATEGORIES.map((interest) => <button key={interest} className={profile.interests.includes(interest) ? 'filter-chip filter-chip--active' : 'filter-chip'} aria-pressed={profile.interests.includes(interest)} onClick={() => toggleInterest(interest)}>{interest}</button>)}</div></fieldset><StatusNotice state={profile.persistenceStatus === 'local' ? 'SUCCESS' : 'UNAVAILABLE'} title={profile.persistenceStatus === 'local' ? 'Local persistence active' : 'Local persistence unavailable'}>This profile is not an account and is not sent to a provider.</StatusNotice></main><PrimaryNavigation /></>
}
