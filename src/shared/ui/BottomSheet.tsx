import type { PropsWithChildren } from 'react'
import { Dialog } from './Dialog'

type BottomSheetProps = PropsWithChildren<{
  isOpen: boolean
  onClose: () => void
  title: string
}>

export function BottomSheet({ isOpen, onClose, title, children }: BottomSheetProps) {
  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} presentation="sheet">
      {children}
    </Dialog>
  )
}
