'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'

type GraphicType = 'chart' | 'diagram' | 'concept' | 'infographic' | 'video' | 'none'
type SourceType = 'personal' | 'client' | 'industry_report' | 'web_source' | 'illustrative'
type ProgressStage = 'preparing' | 'research' | 'draft' | 'graphic' | 'saving' | 'complete' | 'error'

interface ChartData {
  startValue: string
  endValue: string
  timePeriod: string
  dataPoints: string
}

interface DataSource {
  dataPoint: string
  value: string
  sourceType: SourceType
  sourceDescription: string
}

interface FormData {
  author: string
  rawInput: string
  addGraphic: boolean
  graphicDescription: string
  graphicType: GraphicType
  manualTypeSelection: boolean
  uploadedFile: File | null
  chartData: ChartData
  showDataInput: boolean
  dataSources: DataSource[]
  researchUrls: string[]
}

interface ProgressInfo {
  stage: ProgressStage
  message: string
  elapsedSeconds: number
  isVideo: boolean
}

const GRAPHIC_KEYWORDS: Record<GraphicType, string[]> = {
  video: ['video', 'animation', 'animated', 'motion graphics', 'moving', 'clip', 'footage', 'movie'],
  infographic: ['infographic', 'stats', 'statistics visualization', 'data visualization with text', 'text-heavy', 'diagram with text', 'stat card', 'data card', 'metrics dashboard', 'key metrics'],
  chart: ['chart', 'graph', 'data', 'statistics', 'trend', 'numbers', 'metrics', 'percentage', 'growth', 'decline', 'comparison'],
  diagram: ['diagram', 'flow', 'process', 'workflow', 'steps', 'stages', 'architecture', 'structure', 'hierarchy'],
  concept: ['concept', 'illustration', 'visual', 'abstract', 'idea', 'metaphor', 'scene', 'image'],
  none: [],
}

const ENGINE_RECOMMENDATIONS: Record<GraphicType, string> = {
  video: 'Veo 3.1 - Best for animations and motion graphics',
  infographic: 'Nano Banana Pro - Best for text-heavy infographics and data summaries',
  chart: 'Python/Matplotlib - Best for data visualization and charts',
  diagram: 'Python/Matplotlib - Best for process diagrams and flowcharts',
  concept: 'DALL-E 3 - Best for conceptual illustrations and creative visuals',
  none: '',
}

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  personal: 'Personal knowledge',
  client: 'Client data',
  industry_report: 'Industry report',
  web_source: 'Web source',
  illustrative: 'Illustrative (not real data)',
}

function detectGraphicType(description: string): GraphicType {
  const lowerDesc = description.toLowerCase()

  for (const [type, keywords] of Object.entries(GRAPHIC_KEYWORDS)) {
    if (type === 'none') continue
    if (keywords.some(keyword => lowerDesc.includes(keyword))) {
      return type as GraphicType
    }
  }

  return 'concept' // Default to concept if no specific keywords found
}

// Progress Modal Component
function ProgressModal({ progress, onClose }: { progress: ProgressInfo; onClose: () => void }) {
  const router = useRouter()
  const stages: { key: ProgressStage; label: string }[] = [
    { key: 'preparing', label: 'Preparing submission' },
    { key: 'research', label: 'Fetching research URLs' },
    { key: 'draft', label: 'Generating AI draft' },
    { key: 'graphic', label: progress.isVideo ? 'Generating video (1-3 min)' : 'Creating graphic' },
    { key: 'saving', label: 'Saving to database' },
  ]

  const currentIndex = stages.findIndex(s => s.key === progress.stage)
  const isComplete = progress.stage === 'complete'
  const isError = progress.stage === 'error'

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4">
        {/* Header */}
        <div className="text-center mb-6">
          {isComplete ? (
            progress.isVideo ? (
              <>
                <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900">Video Generation In Progress!</h3>
                <p className="text-gray-600 mt-2">Your post text has been saved.</p>
                <p className="text-gray-600 mt-1">The video is still being generated and will appear in the Review Dashboard in <strong>1-3 minutes</strong>.</p>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mt-4">
                  <p className="text-yellow-800 text-sm">Check back shortly - the video will appear once processing completes.</p>
                </div>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900">Submission Complete!</h3>
                <p className="text-gray-600 mt-2">Your content is ready for review.</p>
              </>
            )
          ) : isError ? (
            <>
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900">Something went wrong</h3>
              <p className="text-gray-600 mt-2">{progress.message}</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-linkedin-primary bg-opacity-10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-linkedin-primary animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900">Processing Your Submission</h3>
              <p className="text-gray-600 mt-2">
                Elapsed: <span className="font-mono font-medium">{formatTime(progress.elapsedSeconds)}</span>
              </p>
            </>
          )}
        </div>

        {/* Progress Steps */}
        {!isComplete && !isError && (
          <div className="space-y-3 mb-6">
            {stages.map((stage, index) => {
              const isActive = stage.key === progress.stage
              const isCompleted = index < currentIndex
              const isPending = index > currentIndex

              return (
                <div key={stage.key} className="flex items-center space-x-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isCompleted ? 'bg-green-500' :
                    isActive ? 'bg-linkedin-primary' :
                    'bg-gray-200'
                  }`}>
                    {isCompleted ? (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : isActive ? (
                      <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                    ) : (
                      <div className="w-2 h-2 bg-gray-400 rounded-full" />
                    )}
                  </div>
                  <span className={`text-sm ${
                    isActive ? 'text-linkedin-primary font-medium' :
                    isCompleted ? 'text-green-600' :
                    'text-gray-400'
                  }`}>
                    {stage.label}
                    {isActive && progress.isVideo && stage.key === 'graphic' && (
                      <span className="block text-xs text-gray-500 mt-0.5">
                        Video generation takes longer - please wait
                      </span>
                    )}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Video Warning */}
        {!isComplete && !isError && progress.isVideo && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
            <p className="text-sm text-yellow-800">
              <span className="font-medium">Video generation in progress.</span> This typically takes 1-3 minutes. Please don&apos;t close this window.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex space-x-3">
          {isComplete ? (
            <>
              <button
                onClick={() => router.push('/review')}
                className="flex-1 px-4 py-3 bg-linkedin-primary text-white rounded-lg font-medium hover:bg-linkedin-dark transition-colors"
              >
                {progress.isVideo ? 'Check Progress in Dashboard' : 'Go to Review Dashboard'}
              </button>
              <button
                onClick={onClose}
                className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Submit Another
              </button>
            </>
          ) : isError ? (
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-linkedin-primary text-white rounded-lg font-medium hover:bg-linkedin-dark transition-colors"
            >
              Try Again
            </button>
          ) : (
            <p className="text-xs text-gray-500 text-center w-full">
              Please keep this window open until processing completes
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ContentSubmissionForm() {
  const router = useRouter()
  const [formData, setFormData] = useState<FormData>({
    author: '',
    rawInput: '',
    addGraphic: false,
    graphicDescription: '',
    graphicType: 'none',
    manualTypeSelection: false,
    uploadedFile: null,
    chartData: {
      startValue: '',
      endValue: '',
      timePeriod: '',
      dataPoints: '',
    },
    showDataInput: false,
    dataSources: [],
    researchUrls: [''],
  })

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [showResearchSection, setShowResearchSection] = useState(false)
  const [showSourcesSection, setShowSourcesSection] = useState(false)
  const [showProgressModal, setShowProgressModal] = useState(false)
  const [progressInfo, setProgressInfo] = useState<ProgressInfo>({
    stage: 'preparing',
    message: '',
    elapsedSeconds: 0,
    isVideo: false,
  })
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Check if form has valid content (either idea or graphic)
  const hasIdeaContent = formData.rawInput.trim().length > 0
  const hasGraphicContent = formData.addGraphic && formData.graphicDescription.trim().length > 0
  const hasValidContent = hasIdeaContent || hasGraphicContent
  const hasAuthor = formData.author.trim().length > 0
  const canSubmit = hasAuthor && hasValidContent

  // Auto-detect graphic type when description changes
  useEffect(() => {
    if (formData.graphicDescription && !formData.manualTypeSelection) {
      const detectedType = detectGraphicType(formData.graphicDescription)
      setFormData(prev => ({ ...prev, graphicType: detectedType }))
    }
  }, [formData.graphicDescription, formData.manualTypeSelection])

  // Auto-show sources section when chart data has values
  useEffect(() => {
    const hasChartValues = formData.chartData.startValue ||
                          formData.chartData.endValue ||
                          formData.chartData.dataPoints
    if (hasChartValues && formData.dataSources.length === 0) {
      // Auto-add a source entry when data is entered
      setFormData(prev => ({
        ...prev,
        dataSources: [{
          dataPoint: 'Chart data',
          value: '',
          sourceType: 'personal',
          sourceDescription: ''
        }]
      }))
    }
  }, [formData.chartData, formData.dataSources.length])

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [])

  const handleCloseProgressModal = () => {
    setShowProgressModal(false)
    if (progressInfo.stage === 'complete') {
      // Reset form on successful completion
      setFormData({
        author: '',
        rawInput: '',
        addGraphic: false,
        graphicDescription: '',
        graphicType: 'none',
        manualTypeSelection: false,
        uploadedFile: null,
        chartData: {
          startValue: '',
          endValue: '',
          timePeriod: '',
          dataPoints: '',
        },
        showDataInput: false,
        dataSources: [],
        researchUrls: [''],
      })
      setShowResearchSection(false)
      setShowSourcesSection(false)
    }
    setProgressInfo({
      stage: 'preparing',
      message: '',
      elapsedSeconds: 0,
      isVideo: false,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)
    setSubmitStatus(null)

    // Validate: must have either idea or graphic description
    if (!hasValidContent) {
      setValidationError('Please enter an idea, a graphic description, or both')
      return
    }

    // Determine what we're processing
    const hasResearchUrls = formData.researchUrls.some(url => url.trim())
    const hasIdea = formData.rawInput.trim().length > 0
    const hasGraphic = formData.addGraphic && formData.graphicDescription.trim().length > 0
    const isVideo = formData.graphicType === 'video'

    // Show progress modal
    setShowProgressModal(true)
    setProgressInfo({
      stage: 'preparing',
      message: '',
      elapsedSeconds: 0,
      isVideo,
    })
    setIsSubmitting(true)

    // Start elapsed time counter
    let elapsed = 0
    timerRef.current = setInterval(() => {
      elapsed += 1
      setProgressInfo(prev => ({ ...prev, elapsedSeconds: elapsed }))
    }, 1000)

    try {
      const submitFormData = new FormData()
      submitFormData.append('author', formData.author)

      // Only append idea if provided
      if (formData.rawInput.trim()) {
        submitFormData.append('idea', formData.rawInput)
      }

      if (formData.addGraphic && formData.graphicDescription.trim()) {
        submitFormData.append('graphic_description', formData.graphicDescription)
        submitFormData.append('graphic_type', formData.graphicType)

        if (formData.uploadedFile) {
          submitFormData.append('image_file', formData.uploadedFile)
        }

        // Include chart data if provided (for charts or diagrams)
        if ((formData.graphicType === 'chart' || formData.graphicType === 'diagram') && formData.showDataInput) {
          const hasData = formData.chartData.startValue || formData.chartData.endValue || formData.chartData.dataPoints
          if (hasData) {
            const chartDataJson = JSON.stringify(formData.chartData)
            submitFormData.append('chart_data', chartDataJson)
          }
        }
      }

      // Include data sources if any
      if (formData.dataSources.length > 0) {
        const validSources = formData.dataSources.filter(s => s.dataPoint || s.value)
        if (validSources.length > 0) {
          submitFormData.append('data_sources', JSON.stringify(validSources))
        }
      }

      // Include research URLs if any
      const validUrls = formData.researchUrls.filter(url => url.trim())
      if (validUrls.length > 0) {
        submitFormData.append('research_urls', JSON.stringify(validUrls))
      }

      // Update progress stages based on what we're doing
      // Stage 1: Research (if URLs provided)
      if (hasResearchUrls) {
        setProgressInfo(prev => ({ ...prev, stage: 'research' }))
        await new Promise(resolve => setTimeout(resolve, 500)) // Brief pause to show stage
      }

      // Stage 2: Draft (if idea provided)
      if (hasIdea) {
        setProgressInfo(prev => ({ ...prev, stage: 'draft' }))
      }

      // Stage 3: Graphic (if graphic requested)
      if (hasGraphic) {
        setProgressInfo(prev => ({ ...prev, stage: 'graphic' }))
      }

      // Make the actual API call - no timeout for video (can take 5+ minutes)
      const timeoutMs = isVideo ? 600000 : 300000 // 10 min for video, 5 min otherwise
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

      // For long-running requests (especially video), call backend directly to bypass Next.js proxy timeout
      // The proxy has a ~30s default timeout that can't be reliably extended
      const apiUrl = isVideo || hasResearchUrls
        ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
        : ''  // Use proxy for quick requests

      let response: Response
      try {
        response = await fetch(`${apiUrl}/api/submit-idea`, {
          method: 'POST',
          body: submitFormData,
          signal: controller.signal,
        })
      } catch (fetchError) {
        clearTimeout(timeoutId)
        if (fetchError instanceof Error && fetchError.name === 'AbortError') {
          throw new Error('Request timed out. Your submission may still be processing - please check the Review Dashboard.')
        }
        throw fetchError
      }

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText || 'Failed to submit idea')
      }

      // Parse and validate the response
      let data
      try {
        data = await response.json()
        console.log('Backend response:', data)
        console.log('Response success:', data?.success)
      } catch (parseError) {
        console.error('Failed to parse response JSON:', parseError)
        throw new Error('Invalid response from server')
      }

      // Verify we got a valid success response
      if (!data || !data.success) {
        console.error('Response missing success field:', data)
        throw new Error(data?.message || 'Submission failed - invalid response')
      }

      // Stage 4: Saving
      setProgressInfo(prev => ({ ...prev, stage: 'saving' }))
      await new Promise(resolve => setTimeout(resolve, 500))

      // Complete! Only mark complete after we've verified the response
      console.log('Marking submission as complete')
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setProgressInfo(prev => ({ ...prev, stage: 'complete' }))

    } catch (error) {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }

      const errorMessage = error instanceof Error ? error.message : 'Failed to submit idea'
      setProgressInfo(prev => ({
        ...prev,
        stage: 'error',
        message: errorMessage,
      }))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setFormData(prev => ({ ...prev, uploadedFile: file }))
  }

  const addDataSource = () => {
    setFormData(prev => ({
      ...prev,
      dataSources: [...prev.dataSources, {
        dataPoint: '',
        value: '',
        sourceType: 'personal',
        sourceDescription: ''
      }]
    }))
  }

  const updateDataSource = (index: number, field: keyof DataSource, value: string) => {
    setFormData(prev => ({
      ...prev,
      dataSources: prev.dataSources.map((source, i) =>
        i === index ? { ...source, [field]: value } : source
      )
    }))
  }

  const removeDataSource = (index: number) => {
    setFormData(prev => ({
      ...prev,
      dataSources: prev.dataSources.filter((_, i) => i !== index)
    }))
  }

  const addResearchUrl = () => {
    setFormData(prev => ({
      ...prev,
      researchUrls: [...prev.researchUrls, '']
    }))
  }

  const updateResearchUrl = (index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      researchUrls: prev.researchUrls.map((url, i) => i === index ? value : url)
    }))
  }

  const removeResearchUrl = (index: number) => {
    setFormData(prev => ({
      ...prev,
      researchUrls: prev.researchUrls.filter((_, i) => i !== index)
    }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {submitStatus && (
        <div
          className={`p-4 rounded-lg ${
            submitStatus.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {submitStatus.message}
        </div>
      )}

      {/* Validation Error */}
      {validationError && (
        <div className="p-4 rounded-lg bg-red-50 text-red-800 border border-red-200">
          {validationError}
        </div>
      )}

      {/* Author Input */}
      <div>
        <label htmlFor="author" className="block text-sm font-medium text-gray-700 mb-2">
          Your Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          id="author"
          value={formData.author}
          onChange={(e) => setFormData(prev => ({ ...prev, author: e.target.value }))}
          required
          placeholder="Enter your name"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent transition-colors bg-white"
        />
      </div>

      {/* Raw Input */}
      <div>
        <label htmlFor="rawInput" className="block text-sm font-medium text-gray-700 mb-2">
          Your Raw Idea <span className="text-gray-400">(optional - leave blank if you only need a graphic)</span>
        </label>
        <textarea
          id="rawInput"
          value={formData.rawInput}
          onChange={(e) => setFormData(prev => ({ ...prev, rawInput: e.target.value }))}
          rows={8}
          placeholder="Enter your insight for a LinkedIn post, or skip if you just need a chart/image..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent transition-colors resize-none"
        />
        <p className="mt-1 text-sm text-gray-500">
          {formData.rawInput.length} characters
        </p>
      </div>

      {/* Research URLs Section */}
      <div className="border border-gray-200 rounded-lg">
        <button
          type="button"
          onClick={() => setShowResearchSection(!showResearchSection)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-linkedin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
            <span className="text-sm font-medium text-gray-700">Add Research URLs (optional)</span>
          </div>
          <span className="text-gray-400">{showResearchSection ? '▼' : '▶'}</span>
        </button>

        {showResearchSection && (
          <div className="px-4 pb-4 space-y-3">
            <p className="text-xs text-gray-500">
              Paste URLs to articles, reports, or research. AI will extract relevant facts and cite sources in the post.
            </p>

            {formData.researchUrls.map((url, index) => (
              <div key={index} className="flex items-center space-x-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateResearchUrl(index, e.target.value)}
                  placeholder="https://example.com/article..."
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent"
                />
                {formData.researchUrls.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeResearchUrl(index)}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            ))}

            <button
              type="button"
              onClick={addResearchUrl}
              className="text-sm text-linkedin-primary hover:text-linkedin-dark font-medium flex items-center space-x-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Add another URL</span>
            </button>
          </div>
        )}
      </div>

      {/* Add Graphic Checkbox */}
      <div className="flex items-center">
        <input
          type="checkbox"
          id="addGraphic"
          checked={formData.addGraphic}
          onChange={(e) => setFormData(prev => ({ ...prev, addGraphic: e.target.checked }))}
          className="h-4 w-4 text-linkedin-primary focus:ring-linkedin-primary border-gray-300 rounded"
        />
        <label htmlFor="addGraphic" className="ml-2 text-sm text-gray-700">
          Add a graphic to this post
        </label>
      </div>

      {/* Graphic Options */}
      {formData.addGraphic && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div>
            <label htmlFor="graphicDescription" className="block text-sm font-medium text-gray-700 mb-2">
              Describe the graphic you want
            </label>
            <textarea
              id="graphicDescription"
              value={formData.graphicDescription}
              onChange={(e) => setFormData(prev => ({ ...prev, graphicDescription: e.target.value }))}
              rows={3}
              placeholder="e.g., 'A bar chart showing supply chain cost savings over 5 years' or 'A concept image of global logistics network'"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent transition-colors resize-none"
            />
          </div>

          {/* Auto-detected type and recommendation */}
          {formData.graphicDescription && formData.graphicType !== 'none' && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-800">
                <span className="font-medium">Detected type:</span> {formData.graphicType.charAt(0).toUpperCase() + formData.graphicType.slice(1)}
              </p>
              <p className="text-sm text-blue-700 mt-1">
                <span className="font-medium">Recommended engine:</span> {ENGINE_RECOMMENDATIONS[formData.graphicType]}
              </p>
            </div>
          )}

          {/* Chart Data Input (for chart or diagram types) */}
          {(formData.graphicType === 'chart' || formData.graphicType === 'diagram') && (
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, showDataInput: !prev.showDataInput }))}
                className="text-sm text-linkedin-primary hover:text-linkedin-dark font-medium flex items-center space-x-1"
              >
                <span>{formData.showDataInput ? '▼' : '▶'}</span>
                <span>Add specific data points (optional)</span>
              </button>

              {formData.showDataInput && (
                <div className="p-4 bg-white rounded-lg border border-gray-200 space-y-4">
                  <p className="text-xs text-gray-500">
                    Enter real data for accurate charts. If left blank, illustrative example data will be used.
                    <br />
                    <span className="text-blue-600">Tip: You can also add research URLs above - data will be extracted automatically!</span>
                  </p>

                  {/* Simple Before/After Data */}
                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-2">Option A: Before/After Values</p>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Start Value
                        </label>
                        <input
                          type="text"
                          value={formData.chartData.startValue}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            chartData: { ...prev.chartData, startValue: e.target.value }
                          }))}
                          placeholder="e.g., $100K"
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          End Value
                        </label>
                        <input
                          type="text"
                          value={formData.chartData.endValue}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            chartData: { ...prev.chartData, endValue: e.target.value }
                          }))}
                          placeholder="e.g., $150K"
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Time Period
                        </label>
                        <input
                          type="text"
                          value={formData.chartData.timePeriod}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            chartData: { ...prev.chartData, timePeriod: e.target.value }
                          }))}
                          placeholder="e.g., Q1-Q4 2024"
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Advanced: Multiple Data Points */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Option B: Multiple Data Points
                    </label>
                    <textarea
                      value={formData.chartData.dataPoints}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        chartData: { ...prev.chartData, dataPoints: e.target.value }
                      }))}
                      rows={3}
                      placeholder="Enter structured data, e.g.:
Opus 4.5: $5 input, $25 output
Sonnet 4.5: $3 input, $15 output
Haiku 3.5: $0.25 input, $1.25 output"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-primary focus:border-transparent resize-none"
                    />
                  </div>

                  {/* Data Sources Section */}
                  <div className="border-t border-gray-200 pt-4 mt-4">
                    <button
                      type="button"
                      onClick={() => setShowSourcesSection(!showSourcesSection)}
                      className="text-sm text-linkedin-primary hover:text-linkedin-dark font-medium flex items-center space-x-1"
                    >
                      <span>{showSourcesSection ? '▼' : '▶'}</span>
                      <span>Add data sources (recommended)</span>
                    </button>

                    {showSourcesSection && (
                      <div className="mt-3 space-y-3">
                        <p className="text-xs text-gray-500">
                          Track where your data comes from for accuracy verification.
                        </p>

                        {formData.dataSources.map((source, index) => (
                          <div key={index} className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-gray-600">Source {index + 1}</span>
                              <button
                                type="button"
                                onClick={() => removeDataSource(index)}
                                className="text-red-500 hover:text-red-700 text-xs"
                              >
                                Remove
                              </button>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <input
                                type="text"
                                value={source.dataPoint}
                                onChange={(e) => updateDataSource(index, 'dataPoint', e.target.value)}
                                placeholder="Data point (e.g., 'Cost savings')"
                                className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-linkedin-primary"
                              />
                              <input
                                type="text"
                                value={source.value}
                                onChange={(e) => updateDataSource(index, 'value', e.target.value)}
                                placeholder="Value (e.g., '23%')"
                                className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-linkedin-primary"
                              />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <select
                                value={source.sourceType}
                                onChange={(e) => updateDataSource(index, 'sourceType', e.target.value)}
                                className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-linkedin-primary bg-white"
                              >
                                {Object.entries(SOURCE_TYPE_LABELS).map(([value, label]) => (
                                  <option key={value} value={value}>{label}</option>
                                ))}
                              </select>
                              <input
                                type="text"
                                value={source.sourceDescription}
                                onChange={(e) => updateDataSource(index, 'sourceDescription', e.target.value)}
                                placeholder="Source details (optional)"
                                className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-linkedin-primary"
                              />
                            </div>
                          </div>
                        ))}

                        <button
                          type="button"
                          onClick={addDataSource}
                          className="text-xs text-linkedin-primary hover:text-linkedin-dark font-medium flex items-center space-x-1"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                          <span>Add data source</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Advanced Options Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-linkedin-primary hover:text-linkedin-dark font-medium"
          >
            {showAdvanced ? '▼ Hide advanced options' : '▶ Show advanced options'}
          </button>

          {showAdvanced && (
            <div className="space-y-4 pt-2">
              {/* Manual Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Manually select graphic type
                </label>
                <div className="flex flex-wrap gap-2">
                  {(['chart', 'diagram', 'concept', 'infographic', 'video'] as GraphicType[]).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setFormData(prev => ({
                        ...prev,
                        graphicType: type,
                        manualTypeSelection: true,
                      }))}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        formData.graphicType === type && formData.manualTypeSelection
                          ? 'bg-linkedin-primary text-white'
                          : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({
                      ...prev,
                      manualTypeSelection: false,
                      graphicType: detectGraphicType(prev.graphicDescription),
                    }))}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                  >
                    Auto-detect
                  </button>
                </div>
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Or upload an image instead
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-medium
                    file:bg-linkedin-primary file:text-white
                    hover:file:bg-linkedin-dark
                    file:cursor-pointer cursor-pointer"
                />
                {formData.uploadedFile && (
                  <p className="mt-2 text-sm text-gray-600">
                    Selected: {formData.uploadedFile.name}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting || !canSubmit}
        className={`w-full py-3 px-6 rounded-lg font-medium text-white transition-colors ${
          isSubmitting || !canSubmit
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-linkedin-primary hover:bg-linkedin-dark'
        }`}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </span>
        ) : (
          'Submit Idea'
        )}
      </button>

      {/* Progress Modal */}
      {showProgressModal && (
        <ProgressModal
          progress={progressInfo}
          onClose={handleCloseProgressModal}
        />
      )}
    </form>
  )
}
