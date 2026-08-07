import type { Locale } from '../../../shared/i18n'
import type { PlaceCategory } from '../../place'

export type VisitorMode = 'foreigner' | 'domestic-traveler' | 'local-explorer'

export type TravelerProfile = {
  locale: Locale
  visitorMode: VisitorMode
  interests: PlaceCategory[]
  persistenceStatus: 'local' | 'unavailable'
}
