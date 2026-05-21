'use client'
import { createContext, useContext, useState, type ReactNode } from 'react'

interface ApiKeyContextValue {
  apiKey: string
  setApiKey: (key: string) => void
  geminiKey: string
  setGeminiKey: (key: string) => void
  modalOpen: boolean
  openModal: () => void
  closeModal: () => void
}

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null)

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState('')
  const [geminiKey, setGeminiKey] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  return (
    <ApiKeyContext.Provider value={{
      apiKey,
      setApiKey,
      geminiKey,
      setGeminiKey,
      modalOpen,
      openModal: () => setModalOpen(true),
      closeModal: () => setModalOpen(false),
    }}>
      {children}
    </ApiKeyContext.Provider>
  )
}

export function useApiKey(): ApiKeyContextValue {
  const ctx = useContext(ApiKeyContext)
  if (!ctx) throw new Error('useApiKey must be used within ApiKeyProvider')
  return ctx
}
