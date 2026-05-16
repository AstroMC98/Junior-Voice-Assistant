import AppShell from '@/components/layout/AppShell'
import GuideCreator from '@/components/guide-creator/GuideCreator'
import RecentGuides from '@/components/guide-creator/RecentGuides'

export default function Home() {
  return (
    <AppShell title="Junior">
      <GuideCreator />
      <RecentGuides />
    </AppShell>
  )
}
