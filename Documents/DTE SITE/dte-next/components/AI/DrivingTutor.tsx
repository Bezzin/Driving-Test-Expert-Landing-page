'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageSquare, X, Send, Loader2 } from 'lucide-react'
import { ChatMessage } from '@/lib/types'

// Using a standard variable since this is client-side demo code.
// In production, this would be proxied or use a public-safe key with quotas.
const API_KEY = process.env.NEXT_PUBLIC_GEMINI_API_KEY || ''

export const DrivingTutor: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'model', text: 'Hello! I am your AI Driving Instructor. Ask me anything about the UK driving test, road signs, or difficult maneuvers!' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isOpen])

  const handleSend = async () => {
    if (!input.trim() || !API_KEY) return

    const userMsg = input
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: userMsg }])
    setIsLoading(true)

    try {
      // Dynamic import to avoid bundling @google/genai when API key is not set
      const { GoogleGenAI } = await import('@google/genai')
      const ai = new GoogleGenAI({ apiKey: API_KEY })
      const model = 'gemini-2.5-flash'

      const response = await ai.models.generateContent({
        model,
        contents: [
          { role: 'user', parts: [{ text: `You are a strict but encouraging UK Driving Test Examiner. Answer the following question briefly and accurately based on UK DVSA standards: ${userMsg}` }] }
        ]
      })

      const text = response.text || "I'm sorry, I couldn't process that right now. Please check your connection."

      setMessages(prev => [...prev, { role: 'model', text }])
    } catch {
      setMessages(prev => [...prev, { role: 'model', text: "Sorry, I'm having trouble connecting to the DVSA database (API Error)." }])
    } finally {
      setIsLoading(false)
    }
  }

  if (!API_KEY) return null // Don't show if no key configured

  return (
    <>
      {/* Floating Trigger */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-40 bg-accent text-black p-4 rounded-full shadow-[0_0_20px_rgba(252,163,17,0.5)] transition-transform hover:scale-110 active:scale-95 ${isOpen ? 'hidden' : 'flex'}`}
      >
        <MessageSquare size={28} strokeWidth={2.5} />
      </button>

      {/* Chat Window */}
      <div className={`fixed bottom-6 right-6 z-50 w-[90vw] md:w-[400px] h-[500px] bg-card border border-white/10 rounded-2xl shadow-2xl flex flex-col transition-all duration-300 origin-bottom-right ${isOpen ? 'scale-100 opacity-100' : 'scale-90 opacity-0 pointer-events-none'}`}>

        {/* Header */}
        <div className="p-4 border-b border-white/10 flex justify-between items-center bg-accent/5 rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center font-bold text-black text-xs">AI</div>
            <div>
              <h3 className="font-bold text-white text-sm">Driving Instructor AI</h3>
              <p className="text-xs text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400"></span> Online</p>
            </div>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-white/50 hover:text-white"><X size={20} /></button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${msg.role === 'user' ? 'bg-accent text-black rounded-tr-sm' : 'bg-white/10 text-white rounded-tl-sm'}`}>
                {msg.text}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 rounded-2xl px-4 py-3 rounded-tl-sm">
                <Loader2 className="w-4 h-4 animate-spin text-white/50" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/10">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend() }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about roundabouts..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white focus:outline-none focus:border-accent transition"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-accent text-black p-2.5 rounded-xl hover:bg-white transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </>
  )
}
