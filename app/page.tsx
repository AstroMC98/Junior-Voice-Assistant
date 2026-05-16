import GuideCreator from '@/components/guide-creator/GuideCreator'

export default function Home() {
  return (
    <main className="max-w-xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-slate-100 tracking-tight">Junior</h1>
        <p className="mt-2 text-slate-400 text-lg">
          Load a guide. Speak freely. Keep your hands free.
        </p>
      </div>
      <GuideCreator />
    </main>
  )
}
