import ContentSubmissionForm from '@/components/ContentSubmissionForm'

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Submit Content Idea</h1>
        <p className="mt-2 text-gray-600">
          Share your raw idea and let AI transform it into a professional LinkedIn post.
        </p>
      </div>
      <ContentSubmissionForm />
    </div>
  )
}
