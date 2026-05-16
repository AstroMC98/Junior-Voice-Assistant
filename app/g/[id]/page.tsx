import { notFound } from 'next/navigation'
import { getGuide } from '@/lib/kv'
import AppShell from '@/components/layout/AppShell'
import SessionView from '@/components/session/SessionView'

export default async function GuidePage({ params }: { params: { id: string } }) {
  const guide = await getGuide(params.id)
  if (!guide) notFound()

  return (
    <AppShell title={guide.title} backHref="/" fillHeight>
      <SessionView guide={guide} />
    </AppShell>
  )
}
