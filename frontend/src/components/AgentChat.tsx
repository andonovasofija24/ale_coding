import { useEffect, useRef } from 'react'
import { AgentMessage } from '../types'
import { Bot, User } from 'lucide-react'

interface Props {
  messages: AgentMessage[]
  isLoading: boolean
}

export default function AgentChat({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2">
        <Bot size={32} className="opacity-40" />
        <p>Submit your code to get AI feedback on the current step.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto h-full pr-1">
      {messages.map((msg, i) => (
        <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          {msg.role === 'assistant' && (
            <div className="shrink-0 w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center">
              <Bot size={14} className="text-blue-600" />
            </div>
          )}
          <div
            className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
            }`}
          >
            {msg.content}
          </div>
          {msg.role === 'user' && (
            <div className="shrink-0 w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center">
              <User size={14} className="text-gray-600" />
            </div>
          )}
        </div>
      ))}
      {isLoading && (
        <div className="flex gap-2 justify-start">
          <div className="shrink-0 w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center">
            <Bot size={14} className="text-blue-600" />
          </div>
          <div className="bg-gray-100 rounded-xl rounded-bl-sm px-4 py-3">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
