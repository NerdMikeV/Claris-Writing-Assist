'use client'

import { useState, useEffect } from 'react'

interface DataSource {
  dataPoint: string
  value: string
  sourceType: string
  sourceDescription?: string
}

interface ExtractedFact {
  fact: string
  type: string
  citation_text: string
}

interface ResearchResult {
  url: string
  source_name: string
  extracted_facts: ExtractedFact[]
  summary: string
  relevance_score: number
  error?: boolean
}

interface Submission {
  id: string
  author: string
  raw_input: string
  ai_draft: string | null
  graphic_description: string | null
  graphic_type: string | null
  graphic_data: string | null
  status: string
  created_at: string
  reviewed_at: string | null
  data_sources: DataSource[] | null
  research_urls: ResearchResult[] | null
}

const MAX_LINKEDIN_CHARS = 1200
const WARNING_THRESHOLD = 1100
const HOOK_LINE_COUNT = 3

const SOURCE_TYPE_LABELS: Record<string, string> = {
  personal: 'Personal knowledge',
  client: 'Client data',
  industry_report: 'Industry report',
  web_source: 'Web source',
  illustrative: 'Illustrative (not real)',
}

export default function ReviewDashboard() {
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null)
  const [editedDraft, setEditedDraft] = useState('')
  const [regenerateFeedback, setRegenerateFeedback] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copySuccess, setCopySuccess] = useState(false)
  const [imageVariations, setImageVariations] = useState<string[]>([])
  const [isGeneratingVariations, setIsGeneratingVariations] = useState(false)
  const [showVariationsModal, setShowVariationsModal] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const fetchSubmissions = async () => {
    try {
      const response = await fetch('/api/pending-submissions')
      if (!response.ok) throw new Error('Failed to fetch submissions')
      const data = await response.json()
      setSubmissions(data)
    } catch (err) {
      setError('Failed to load submissions')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchSubmissions()
  }, [])

  useEffect(() => {
    if (selectedSubmission) {
      setEditedDraft(selectedSubmission.ai_draft || '')
    }
  }, [selectedSubmission])

  const handleApprove = async () => {
    if (!selectedSubmission) return
    setIsProcessing(true)

    try {
      const response = await fetch(`/api/approve-submission/${selectedSubmission.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_post: editedDraft }),
      })

      if (!response.ok) throw new Error('Failed to approve submission')

      // Remove from list and reset selection
      setSubmissions(prev => prev.filter(s => s.id !== selectedSubmission.id))
      setSelectedSubmission(null)
      setEditedDraft('')
    } catch (err) {
      setError('Failed to approve submission')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReject = async () => {
    if (!selectedSubmission) return
    setIsProcessing(true)

    try {
      const response = await fetch(`/api/reject-submission/${selectedSubmission.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })

      if (!response.ok) throw new Error('Failed to reject submission')

      // Remove from list and reset selection
      setSubmissions(prev => prev.filter(s => s.id !== selectedSubmission.id))
      setSelectedSubmission(null)
      setEditedDraft('')
    } catch (err) {
      setError('Failed to reject submission')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleRegenerateImage = async () => {
    if (!selectedSubmission || !regenerateFeedback.trim()) return
    setIsRegenerating(true)

    try {
      const response = await fetch(`/api/regenerate-image/${selectedSubmission.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: regenerateFeedback }),
      })

      if (!response.ok) throw new Error('Failed to regenerate image')

      const data = await response.json()

      // Update the selected submission with new image
      setSelectedSubmission(prev => prev ? { ...prev, graphic_data: data.new_image_data } : null)
      setSubmissions(prev =>
        prev.map(s =>
          s.id === selectedSubmission.id ? { ...s, graphic_data: data.new_image_data } : s
        )
      )
      setRegenerateFeedback('')
    } catch (err) {
      setError('Failed to regenerate image')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleCopyText = async () => {
    if (!editedDraft) return
    try {
      await navigator.clipboard.writeText(editedDraft)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000)
    } catch (err) {
      setError('Failed to copy text to clipboard')
    }
  }

  const handleGenerateVariations = async () => {
    if (!selectedSubmission) return
    setIsGeneratingVariations(true)
    setImageVariations([])

    try {
      const response = await fetch(`/api/generate-variations/${selectedSubmission.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!response.ok) throw new Error('Failed to generate variations')

      const data = await response.json()
      setImageVariations(data.variations)
      setShowVariationsModal(true)
    } catch (err) {
      setError('Failed to generate image variations')
    } finally {
      setIsGeneratingVariations(false)
    }
  }

  const handleSelectVariation = async (imageData: string) => {
    if (!selectedSubmission) return
    setIsProcessing(true)

    try {
      const response = await fetch(`/api/select-variation/${selectedSubmission.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_data: imageData }),
      })

      if (!response.ok) throw new Error('Failed to select variation')

      // Update the selected submission with new image
      setSelectedSubmission(prev => prev ? { ...prev, graphic_data: imageData } : null)
      setSubmissions(prev =>
        prev.map(s =>
          s.id === selectedSubmission.id ? { ...s, graphic_data: imageData } : s
        )
      )
      setShowVariationsModal(false)
      setImageVariations([])
    } catch (err) {
      setError('Failed to select variation')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDownloadMedia = () => {
    if (!selectedSubmission?.graphic_data) return

    const mediaSrc = getMediaSrc(selectedSubmission.graphic_data)
    const link = document.createElement('a')
    link.href = mediaSrc

    // Generate filename with date and appropriate extension
    const date = new Date().toISOString().split('T')[0]
    const isVideo = isVideoMedia(selectedSubmission.graphic_data)
    const extension = isVideo ? 'mp4' : 'png'
    link.download = `claris-post-${date}.${extension}`

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Alias for backwards compatibility
  const handleDownloadImage = handleDownloadMedia

  const getCharCountColor = (count: number) => {
    if (count > MAX_LINKEDIN_CHARS) return 'text-red-600'
    if (count > WARNING_THRESHOLD) return 'text-yellow-600'
    return 'text-gray-500'
  }

  // Get hook lines (first 3 lines) for preview
  const getHookLines = (text: string): { hook: string; rest: string } => {
    if (!text) return { hook: '', rest: '' }
    const lines = text.split('\n').filter(line => line.trim() !== '')
    const hookLines = lines.slice(0, HOOK_LINE_COUNT)
    const restLines = lines.slice(HOOK_LINE_COUNT)
    return {
      hook: hookLines.join('\n'),
      rest: restLines.join('\n')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Helper to get proper media src - handles both raw base64 and data URI formats
  const getMediaSrc = (graphicData: string | null): string => {
    if (!graphicData) return ''
    // If it already has the data URI prefix, use as-is
    if (graphicData.startsWith('data:')) {
      return graphicData
    }
    // Otherwise, add the prefix (default to image/png)
    return `data:image/png;base64,${graphicData}`
  }

  // Helper to check if media is video
  const isVideoMedia = (graphicData: string | null): boolean => {
    if (!graphicData) return false
    return graphicData.startsWith('data:video/')
  }

  // Alias for backwards compatibility
  const getImageSrc = getMediaSrc

  // Check if any data sources need attention (illustrative or missing source)
  const hasSourceWarnings = (sources: DataSource[] | null): boolean => {
    if (!sources) return false
    return sources.some(s => s.sourceType === 'illustrative' || !s.sourceType)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-linkedin-primary"></div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Submissions List */}
      <div className="w-80 border-r border-gray-200 bg-white overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Pending Review</h2>
          <p className="text-sm text-gray-500">{submissions.length} submissions</p>
        </div>

        {submissions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No pending submissions
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {submissions.map((submission) => (
              <button
                key={submission.id}
                onClick={() => setSelectedSubmission(submission)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  selectedSubmission?.id === submission.id ? 'bg-blue-50 border-l-4 border-linkedin-primary' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-900">{submission.author}</span>
                  <span className="text-xs text-gray-500">{formatDate(submission.created_at)}</span>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {submission.raw_input
                    ? `${submission.raw_input.substring(0, 100)}...`
                    : submission.graphic_description
                      ? `[Graphic] ${submission.graphic_description.substring(0, 80)}...`
                      : '[Graphic only]'
                  }
                </p>
                <div className="flex items-center gap-2 mt-2">
                  {submission.graphic_type && (
                    <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                      {submission.graphic_type}
                    </span>
                  )}
                  {submission.research_urls && submission.research_urls.length > 0 && (
                    <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                      {submission.research_urls.length} sources
                    </span>
                  )}
                  {hasSourceWarnings(submission.data_sources) && (
                    <span className="inline-block px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded">
                      ⚠️ Verify
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right Panel - Submission Details */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        {error && (
          <div className="m-4 p-4 bg-red-50 text-red-800 rounded-lg border border-red-200">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-600 hover:text-red-800"
            >
              ×
            </button>
          </div>
        )}

        {!selectedSubmission ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a submission to review
          </div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Submission from {selectedSubmission.author}
                </h2>
                <p className="text-sm text-gray-500">
                  Submitted {formatDate(selectedSubmission.created_at)}
                </p>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleReject}
                  disabled={isProcessing}
                  className="px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  Reject
                </button>
                <button
                  onClick={handleApprove}
                  disabled={isProcessing || (!!editedDraft && editedDraft.length > MAX_LINKEDIN_CHARS)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  Approve
                </button>
              </div>
            </div>

            {/* Export Actions - only show if there's content to export */}
            {(editedDraft || selectedSubmission?.graphic_data) && (
              <div className="flex items-center space-x-3 p-4 bg-white rounded-lg shadow">
                <span className="text-sm font-medium text-gray-700">Export:</span>
                {editedDraft && (
                  <button
                    onClick={handleCopyText}
                    className="px-4 py-2 bg-linkedin-primary text-white rounded-lg hover:bg-linkedin-dark transition-colors flex items-center space-x-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                    <span>{copySuccess ? 'Copied!' : 'Copy Text'}</span>
                  </button>
                )}
                {selectedSubmission?.graphic_data && (
                  <button
                    onClick={handleDownloadMedia}
                    className="px-4 py-2 bg-linkedin-primary text-white rounded-lg hover:bg-linkedin-dark transition-colors flex items-center space-x-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>Download {isVideoMedia(selectedSubmission.graphic_data) ? 'Video' : 'Image'}</span>
                  </button>
                )}
              </div>
            )}

            {/* Data Sources Section */}
            {selectedSubmission.data_sources && selectedSubmission.data_sources.length > 0 && (
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-linkedin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Data Sources
                </h3>
                <div className="space-y-2">
                  {selectedSubmission.data_sources.map((source, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${
                        source.sourceType === 'illustrative'
                          ? 'bg-yellow-50 border-yellow-200'
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="font-medium text-gray-800">{source.dataPoint}</span>
                          {source.value && (
                            <span className="ml-2 text-gray-600">: {source.value}</span>
                          )}
                        </div>
                        {source.sourceType === 'illustrative' && (
                          <span className="text-yellow-600 text-xs font-medium flex items-center">
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Not real data
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        Source: {SOURCE_TYPE_LABELS[source.sourceType] || source.sourceType}
                        {source.sourceDescription && ` - ${source.sourceDescription}`}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Research Sources Section */}
            {selectedSubmission.research_urls && selectedSubmission.research_urls.length > 0 && (
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-linkedin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  Research Sources
                </h3>
                <div className="space-y-4">
                  {selectedSubmission.research_urls.map((result, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-linkedin-primary hover:underline font-medium text-sm flex items-center"
                        >
                          {result.source_name}
                          <svg className="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </a>
                        {result.error ? (
                          <span className="text-xs text-red-500">Failed to fetch</span>
                        ) : (
                          <span className="text-xs text-gray-500">
                            Relevance: {result.relevance_score}/10
                          </span>
                        )}
                      </div>

                      {result.summary && (
                        <p className="text-xs text-gray-600 mb-2">{result.summary}</p>
                      )}

                      {result.extracted_facts && result.extracted_facts.length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-gray-500">Extracted Facts:</p>
                          {result.extracted_facts.map((fact, factIndex) => (
                            <div
                              key={factIndex}
                              className="text-xs p-2 bg-blue-50 rounded border-l-2 border-blue-400"
                            >
                              <span className="inline-block px-1 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] mr-2">
                                {fact.type}
                              </span>
                              <span className="text-gray-700">{fact.fact}</span>
                              <p className="text-gray-500 mt-1 italic">{fact.citation_text}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className={`grid gap-6 ${selectedSubmission.ai_draft ? 'grid-cols-2' : 'grid-cols-1'}`}>
              {/* Left Column */}
              <div className="space-y-6">
                {/* Original Input - only show if there's raw_input */}
                {selectedSubmission.raw_input && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Original Raw Input</h3>
                    <div className="p-3 bg-gray-50 rounded text-sm text-gray-800 whitespace-pre-wrap">
                      {selectedSubmission.raw_input}
                    </div>
                  </div>
                )}

                {/* Graphic Description - show if no raw_input but has graphic description */}
                {!selectedSubmission.raw_input && selectedSubmission.graphic_description && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Graphic Description</h3>
                    <div className="p-3 bg-gray-50 rounded text-sm text-gray-800 whitespace-pre-wrap">
                      {selectedSubmission.graphic_description}
                    </div>
                  </div>
                )}

                {/* AI Draft Editor - only show if there's an AI draft */}
                {selectedSubmission.ai_draft && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-700">AI Draft</h3>
                      <span className={`text-sm ${getCharCountColor(editedDraft.length)}`}>
                        {editedDraft.length} / {MAX_LINKEDIN_CHARS} characters
                        {editedDraft.length > MAX_LINKEDIN_CHARS && ' (exceeds limit!)'}
                      </span>
                    </div>
                    <textarea
                      value={editedDraft}
                      onChange={(e) => setEditedDraft(e.target.value)}
                      rows={12}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent resize-none"
                    />
                  </div>
                )}

                {/* Video Generating Indicator */}
                {selectedSubmission.graphic_type === 'video' && !selectedSubmission.graphic_data && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Video Generation</h3>
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                      <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-yellow-600 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                      </div>
                      <p className="text-yellow-800 font-medium">Video is being generated...</p>
                      <p className="text-yellow-700 text-sm mt-1">This typically takes 1-3 minutes. Refresh the page to check for updates.</p>
                      <button
                        onClick={fetchSubmissions}
                        className="mt-3 px-4 py-2 bg-yellow-600 text-white text-sm rounded-lg hover:bg-yellow-700 transition-colors"
                      >
                        Refresh
                      </button>
                    </div>
                  </div>
                )}

                {/* Generated Graphic/Video */}
                {selectedSubmission.graphic_data && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      Generated {isVideoMedia(selectedSubmission.graphic_data) ? 'Video' : 'Graphic'} ({selectedSubmission.graphic_type})
                    </h3>
                    <div className="relative">
                      <div className={isRegenerating ? 'opacity-30' : ''}>
                        {isVideoMedia(selectedSubmission.graphic_data) ? (
                          <video
                            src={getMediaSrc(selectedSubmission.graphic_data)}
                            controls
                            autoPlay
                            loop
                            muted
                            className="w-full rounded-lg border border-gray-200"
                          >
                            Your browser does not support the video tag.
                          </video>
                        ) : (
                          <img
                            src={getImageSrc(selectedSubmission.graphic_data)}
                            alt="Generated graphic"
                            className="w-full rounded-lg border border-gray-200"
                          />
                        )}
                      </div>
                      {isRegenerating && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/70 rounded-lg">
                          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                          <p className="text-gray-700 font-medium">
                            {selectedSubmission.graphic_type === 'video'
                              ? 'Regenerating video... (1-3 min)'
                              : 'Regenerating image...'}
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="mt-4">
                      <label className="block text-sm text-gray-600 mb-2">
                        Request changes to the {isVideoMedia(selectedSubmission.graphic_data) ? 'video' : 'image'}:
                      </label>
                      <textarea
                        value={regenerateFeedback}
                        onChange={(e) => setRegenerateFeedback(e.target.value)}
                        rows={2}
                        placeholder={isVideoMedia(selectedSubmission.graphic_data)
                          ? "e.g., 'Make it slower' or 'Add more transitions'"
                          : "e.g., 'Make the colors more vibrant' or 'Add a title to the chart'"}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent resize-none text-sm"
                      />
                      <div className="flex space-x-2 mt-2">
                        <button
                          onClick={handleRegenerateImage}
                          disabled={isRegenerating || !regenerateFeedback.trim()}
                          className={`px-4 py-2 text-white text-sm rounded-lg transition-colors disabled:opacity-50 flex items-center space-x-2 ${
                            isRegenerating ? 'bg-gray-400 cursor-not-allowed' : 'bg-linkedin-primary hover:bg-linkedin-dark'
                          }`}
                        >
                          {isRegenerating ? (
                            <>
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              <span>Regenerating...</span>
                            </>
                          ) : (
                            <span>Regenerate {isVideoMedia(selectedSubmission.graphic_data) ? 'Video' : 'Image'}</span>
                          )}
                        </button>
                        {!isVideoMedia(selectedSubmission.graphic_data) && (
                          <button
                            onClick={handleGenerateVariations}
                            disabled={isRegenerating || isGeneratingVariations}
                            className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 flex items-center space-x-1"
                          >
                            {isGeneratingVariations ? (
                              <>
                                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                <span>Generating...</span>
                              </>
                            ) : (
                              <>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span>Generate Variations</span>
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column - LinkedIn Preview (only show if there's text content) */}
              {selectedSubmission.ai_draft && (
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-4">LinkedIn Preview</h3>

                  {/* Hook Preview Box */}
                  {editedDraft && (
                    <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-xs font-medium text-yellow-800 mb-2">
                        Hook Preview (what users see before "see more"):
                      </p>
                      <div className="text-sm text-gray-900 font-medium whitespace-pre-wrap">
                        {getHookLines(editedDraft).hook}
                      </div>
                    </div>
                  )}

                  <div className="linkedin-preview border border-gray-200 rounded-lg overflow-hidden">
                    {/* Profile Header */}
                    <div className="p-4 border-b border-gray-100">
                      <div className="flex items-start space-x-3">
                        <div className="w-12 h-12 bg-linkedin-primary rounded-full flex items-center justify-center text-white font-bold">
                          {selectedSubmission.author.charAt(0)}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{selectedSubmission.author}</p>
                          <p className="text-xs text-gray-500">Supply Chain Consultant at Claris</p>
                          <p className="text-xs text-gray-400">Just now</p>
                        </div>
                      </div>
                    </div>

                    {/* Post Content with Hook Highlighting */}
                    <div className="p-4">
                      {editedDraft ? (
                        <div className="text-sm text-gray-800 leading-relaxed">
                          <span className="font-semibold whitespace-pre-wrap">{getHookLines(editedDraft).hook}</span>
                          {getHookLines(editedDraft).rest && (
                            <>
                              <span className="whitespace-pre-wrap">{'\n'}{getHookLines(editedDraft).rest}</span>
                            </>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 italic">No draft content yet...</span>
                      )}
                    </div>

                    {/* Post Image/Video */}
                    {selectedSubmission.graphic_data && (
                      <div className="border-t border-gray-100">
                        {isVideoMedia(selectedSubmission.graphic_data) ? (
                          <video
                            src={getMediaSrc(selectedSubmission.graphic_data)}
                            controls
                            muted
                            loop
                            className="w-full"
                          >
                            Your browser does not support the video tag.
                          </video>
                        ) : (
                          <img
                            src={getImageSrc(selectedSubmission.graphic_data)}
                            alt="Post graphic"
                            className="w-full"
                          />
                        )}
                      </div>
                    )}

                    {/* Engagement Bar */}
                    <div className="p-3 border-t border-gray-100">
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div className="flex items-center space-x-1">
                          <span className="inline-flex items-center justify-center w-4 h-4 bg-blue-500 rounded-full text-white text-[10px]">+</span>
                          <span>0</span>
                        </div>
                        <span>0 comments</span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="px-4 py-2 border-t border-gray-100 flex justify-around">
                      {['Like', 'Comment', 'Repost', 'Send'].map((action) => (
                        <button
                          key={action}
                          className="flex items-center space-x-1 text-gray-500 text-xs px-3 py-2 rounded hover:bg-gray-100"
                        >
                          <span>{action}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Image Variations Modal */}
      {showVariationsModal && imageVariations.length > 0 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Choose a Variation</h3>
                <button
                  onClick={() => {
                    setShowVariationsModal(false)
                    setImageVariations([])
                  }}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Click on an image to select it as your main graphic
              </p>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {imageVariations.map((variation, index) => (
                  <button
                    key={index}
                    onClick={() => handleSelectVariation(variation)}
                    disabled={isProcessing}
                    className="group relative aspect-video rounded-lg overflow-hidden border-2 border-transparent hover:border-linkedin-primary transition-all disabled:opacity-50"
                  >
                    <img
                      src={variation.startsWith('data:') ? variation : `data:image/png;base64,${variation}`}
                      alt={`Variation ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all flex items-center justify-center">
                      <span className="opacity-0 group-hover:opacity-100 bg-white text-gray-800 px-3 py-1.5 rounded-lg text-sm font-medium shadow-lg">
                        Select Option {index + 1}
                      </span>
                    </div>
                    <div className="absolute top-2 left-2 bg-white text-gray-700 px-2 py-0.5 rounded text-xs font-medium">
                      Option {index + 1}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <p className="text-xs text-gray-500 text-center">
                Each variation uses a slightly different style. The original image is shown first.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
