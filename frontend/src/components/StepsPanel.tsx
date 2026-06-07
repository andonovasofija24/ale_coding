import { SessionStep } from '../types'
import { CheckCircle2, Circle, Clock, Zap } from 'lucide-react'

interface Props {
  steps: SessionStep[]
  currentStep: number
  sessionCompleted: boolean
}

export default function StepsPanel({ steps, currentStep, sessionCompleted }: Props) {
  return (
    <div className="flex flex-col gap-1">
      {sessionCompleted && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-2 text-sm text-green-800 font-medium flex items-center gap-2">
          <CheckCircle2 size={16} className="text-green-600" />
          All steps completed! Great work!
        </div>
      )}
      {steps.map((step) => {
        const isActive = step.status === 'active'
        const isDone = step.status === 'completed'
        const isPending = step.status === 'pending'

        return (
          <div
            key={step.id}
            className={`rounded-lg border p-3 transition-all ${
              isActive
                ? 'border-blue-300 bg-blue-50'
                : isDone
                ? 'border-green-200 bg-green-50'
                : 'border-gray-200 bg-white opacity-60'
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 size={16} className="text-green-600" />
                ) : isActive ? (
                  <Circle size={16} className="text-blue-600 fill-blue-100" />
                ) : (
                  <Clock size={16} className="text-gray-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-gray-400">Step {step.step_number + 1}</span>
                  {step.step_type === 'optimization' && (
                    <span className="inline-flex items-center gap-0.5 text-xs bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded">
                      <Zap size={10} /> Optimize
                    </span>
                  )}
                </div>
                <p className={`text-sm font-medium mt-0.5 ${isActive ? 'text-blue-900' : isDone ? 'text-green-900' : 'text-gray-600'}`}>
                  {step.title}
                </p>
                {isActive && (
                  <p className="text-xs text-blue-700 mt-1 leading-relaxed">{step.description}</p>
                )}
                {isDone && step.agent_feedback && (
                  <p className="text-xs text-green-700 mt-1 leading-relaxed">{step.agent_feedback}</p>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
