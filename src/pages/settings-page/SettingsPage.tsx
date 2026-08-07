import { useState } from 'react'
import type { PlaceCategory } from '../../entities/place'
import { PLACE_CATEGORIES } from '../../entities/place'
import type { TravelerProfile, VisitorMode } from '../../entities/traveler-profile'
import { getTravelerProfile, setTravelerProfile } from '../../features/manage-traveler-profile'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Chip, StatusNotice, useToast } from '../../shared/ui'
import { UtilityNavigation } from '../../widgets/app-chrome'

export function SettingsPage() {
  const { locale, setLocale, t } = useI18n(); const [profile, setProfile] = useState<TravelerProfile>(() => getTravelerProfile()); const { pushToast } = useToast()
  const updateProfile = (next: TravelerProfile) => { const persistenceStatus: TravelerProfile['persistenceStatus'] = setTravelerProfile(next) ? 'local' : 'unavailable'; const persisted = { ...next, persistenceStatus }; setProfile(persisted); track('profile_preferences_persisted', { locale: persisted.locale, visitorMode: persisted.visitorMode, interestCount: persisted.interests.length, persistenceStatus }); pushToast({ message: persistenceStatus === 'local' ? t('settings.saved') : t('settings.storageError') }) }
  const updateLocale = (nextLocale: string) => { const next = nextLocale === 'en' ? 'en' : 'ko'; setLocale(next); updateProfile({ ...profile, locale: next }) }
  const toggleInterest = (interest: PlaceCategory) => updateProfile({ ...profile, interests: profile.interests.includes(interest) ? profile.interests.filter((item) => item !== interest) : [...profile.interests, interest] })
  return <main id="main-content" className="product-page"><UtilityNavigation /><header className="surface-header"><p className="eyebrow">SETTINGS</p><h1>{t('settings.title')}</h1><p>{t('settings.description')}</p></header><label className="locale-control"><span>{t('settings.language')}</span><select value={locale} onChange={(event) => updateLocale(event.target.value)}><option value="ko">한국어</option><option value="en">English</option></select></label><fieldset className="settings-fieldset"><legend>{t('settings.visitorMode')}</legend>{(['foreigner', 'domestic-traveler', 'local-explorer'] as VisitorMode[]).map((mode) => <label key={mode}><input type="radio" name="visitor-mode" checked={profile.visitorMode === mode} onChange={() => updateProfile({ ...profile, visitorMode: mode })} /> {t(`label.visitor.${mode}`)}</label>)}</fieldset><fieldset className="settings-fieldset"><legend>{t('settings.interests')}</legend><div className="filter-row">{PLACE_CATEGORIES.map((interest) => <Chip key={interest} selected={profile.interests.includes(interest)} onClick={() => toggleInterest(interest)}>{t(`label.category.${interest}`)}</Chip>)}</div></fieldset><StatusNotice state={profile.persistenceStatus === 'local' ? 'SUCCESS' : 'UNAVAILABLE'} title={profile.persistenceStatus === 'local' ? t('settings.persisted') : t('settings.storageUnavailable')}>{t('settings.profileDescription')}</StatusNotice></main>
}
