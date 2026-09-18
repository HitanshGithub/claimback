import type { Strength, Verdict } from '../api/types'

export interface VerdictMeta {
  /** Chip text */
  label: string
  /** Chip text when the verdict is about a claim-level check rather than a deduction */
  checkLabel: string
  /** Filter tab text */
  tab: string
  /** One-line plain-language meaning */
  meaning: string
  classes: {
    chip: string
    dot: string
    bar: string
    softBg: string
    text: string
    border: string
    ring: string
  }
}

// Class strings are written out in full so Tailwind can see them.
export const VERDICTS: Record<Verdict, VerdictMeta> = {
  challengeable: {
    label: 'You can challenge',
    checkLabel: 'You can challenge',
    tab: 'Challenge',
    meaning: "Not backed by your policy or the rules. You can dispute it.",
    classes: {
      chip: 'bg-challenge-50 text-challenge-700 ring-challenge-200',
      dot: 'bg-challenge-500',
      bar: 'bg-challenge-500',
      softBg: 'bg-challenge-50',
      text: 'text-challenge-700',
      border: 'border-challenge-200',
      ring: 'ring-challenge-200',
    },
  },
  needs_more_info: {
    label: 'Ask for reasons',
    checkLabel: 'Ask the insurer',
    tab: 'Ask for reasons',
    meaning: 'The insurer should justify this before you accept it.',
    classes: {
      chip: 'bg-info-50 text-info-700 ring-info-200',
      dot: 'bg-info-500',
      bar: 'bg-info-500',
      softBg: 'bg-info-50',
      text: 'text-info-700',
      border: 'border-info-200',
      ring: 'ring-info-200',
    },
  },
  fair_ask_hospital_to_absorb: {
    label: 'Ask hospital to waive',
    checkLabel: 'Ask hospital to waive',
    tab: 'Ask hospital',
    meaning: 'Allowed by your policy, but you can ask the hospital to waive it. A request, not a right.',
    classes: {
      chip: 'bg-absorb-50 text-absorb-700 ring-absorb-200',
      dot: 'bg-absorb-500',
      bar: 'bg-absorb-500',
      softBg: 'bg-absorb-50',
      text: 'text-absorb-700',
      border: 'border-absorb-200',
      ring: 'ring-absorb-200',
    },
  },
  fair: {
    label: 'Fair deduction',
    checkLabel: 'Checks out',
    tab: 'Fair',
    meaning: 'Your policy allows this cut.',
    classes: {
      chip: 'bg-fair-50 text-fair-700 ring-fair-200',
      dot: 'bg-fair-500',
      bar: 'bg-fair-500',
      softBg: 'bg-fair-50',
      text: 'text-fair-700',
      border: 'border-fair-200',
      ring: 'ring-fair-200',
    },
  },
  not_applicable: {
    label: "Doesn't apply",
    checkLabel: "Doesn't apply",
    tab: "Doesn't apply",
    meaning: "This check didn't apply to your claim.",
    classes: {
      chip: 'bg-na-50 text-na-700 ring-na-200',
      dot: 'bg-na-500',
      bar: 'bg-na-500',
      softBg: 'bg-na-50',
      text: 'text-na-700',
      border: 'border-na-200',
      ring: 'ring-na-200',
    },
  },
}

/** Display order: what needs action first. */
export const VERDICT_ORDER: Verdict[] = [
  'challengeable',
  'needs_more_info',
  'fair_ask_hospital_to_absorb',
  'fair',
  'not_applicable',
]

export const STRENGTH_LABEL: Record<Strength, string> = {
  strong: 'Strong case',
  moderate: 'Reasonable case',
  weak: 'Weak case',
}

export const STRENGTH_LEVEL: Record<Strength, number> = {
  strong: 3,
  moderate: 2,
  weak: 1,
}

export function strongest(strengths: (Strength | null | undefined)[]): Strength | null {
  let best: Strength | null = null
  for (const s of strengths) {
    if (!s) continue
    if (!best || STRENGTH_LEVEL[s] > STRENGTH_LEVEL[best]) best = s
  }
  return best
}

export function outcomeMeta(decision: string): { label: string; classes: string } {
  switch (decision) {
    case 'allowed':
      return { label: 'Policyholder won', classes: 'bg-fair-50 text-fair-700 ring-fair-200' }
    case 'partly_allowed':
      return { label: 'Partly won', classes: 'bg-info-50 text-info-700 ring-info-200' }
    case 'dismissed':
      return { label: 'Policyholder lost', classes: 'bg-na-50 text-na-800 ring-na-200' }
    default:
      return {
        label: decision.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()),
        classes: 'bg-na-50 text-na-700 ring-na-200',
      }
  }
}
