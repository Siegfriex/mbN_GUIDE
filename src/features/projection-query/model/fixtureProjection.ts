import type { PlaceCategory } from '../../../entities/place'
import { fixturePlaceRepository } from '../../../entities/place'
import { fixtureLiveSessionRepository } from '../../../entities/live-session'
import { fixtureStoryRepository } from '../../../entities/story'

/**
 * The only M-2 fixture adapter entrypoint for page-level consumers.
 * A future release adapter can implement this same projection boundary without
 * exposing raw repository choices to pages or widgets.
 */
export const fixtureProjection = {
  listPlaces(category: PlaceCategory | 'all') {
    return fixturePlaceRepository.list({ category })
  },
  getPlace(placeId: string) {
    return fixturePlaceRepository.getById(placeId)
  },
  listStories() {
    return fixtureStoryRepository.list()
  },
  getStory(storyId: string) {
    return fixtureStoryRepository.getById(storyId)
  },
  listLiveSessions() {
    return fixtureLiveSessionRepository.list()
  },
  getLiveSession(sessionId: string) {
    return fixtureLiveSessionRepository.getById(sessionId)
  },
}
