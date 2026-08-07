import { useState } from 'react'
import { track } from '../../../shared/analytics'
import { Button, useToast } from '../../../shared/ui'
import { useI18n } from '../../../shared/i18n'
import { getSavedItems, setSavedItems } from '../model/savedItemStorage'

type SavePlaceButtonProps = {
  placeId: string
}

export function SavePlaceButton({ placeId }: SavePlaceButtonProps) {
  const [isSaved, setIsSaved] = useState(() => getSavedItems().some((item) => item.targetId === placeId))
  const { pushToast } = useToast()
  const { t } = useI18n()

  const toggleSaved = () => {
    const current = getSavedItems()
    const existing = current.find((item) => item.targetId === placeId)
    const next = existing
      ? current.filter((item) => item.targetId !== placeId)
      : [...current, { id: `saved:${placeId}`, targetType: 'place' as const, targetId: placeId, savedAt: new Date().toISOString(), collection: 'default' as const }]

    if (!setSavedItems(next)) {
      pushToast({ message: t('saved.updateFailed') })
      return
    }

    const saved = !existing
    setIsSaved(saved)
    if (saved) {
      track('item_saved', { targetType: 'place', targetId: placeId, collection: 'default' })
    }
    pushToast({ message: saved ? t('saved.saved') : t('saved.removed') })
  }

  return <Button variant={isSaved ? 'secondary' : 'primary'} onClick={toggleSaved}>{isSaved ? t('common.saved') : t('common.save')}</Button>
}
