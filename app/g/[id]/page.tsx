import { notFound } from 'next/navigation'
import { getGuide } from '@/lib/kv'
import SessionView from '@/components/session/SessionView'

export default async function GuidePage({ params }: { params: { id: string } }) {
  const guide = await getGuide(params.id)
  if (!guide) notFound()

  return (
    <main className="max-w-xl mx-auto px-4 py-8">
      <SessionView guide={guide} />
    </main>
  )
}
