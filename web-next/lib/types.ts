export interface Readability {
  words: number;
  sentences: number;
  flesch_reading_ease: number;
  flesch_kincaid_grade: number | null;
}

export interface Faithfulness {
  ok: boolean;
  dropped_quantities: string[];
  invented_quantities: string[];
  dropped_dates: string[];
  invented_dates: string[];
  warnings: string[];
}

export interface SimplifyResult {
  level: string;
  original: string;
  simplified: string;
  source_readability: Readability;
  output_readability: Readability;
  faithfulness: Faithfulness;
}

export interface SemanticIssue {
  type: string;
  detail: string;
}

export interface SemanticReport {
  available: boolean;
  faithful: boolean | null;
  issues: SemanticIssue[];
}

export interface ReviewSummary {
  id: number;
  created_at: string;
  updated_at: string;
  title: string;
  lang: string;
  level: string;
  kind: string;
  status: string;
  faithful: boolean | null;
}

export interface ReviewComment {
  id: number;
  created_at: string;
  author: string;
  body: string;
}

export interface ReviewVersion {
  id: number;
  created_at: string;
  output: string;
  note: string | null;
  faithful: boolean | null;
}

export interface Review extends ReviewSummary {
  source: string;
  output: string;
  meta: unknown;
  versions: ReviewVersion[];
  comments: ReviewComment[];
}

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ru", label: "Русский" },
  { code: "es", label: "Español" },
  { code: "de", label: "Deutsch" },
  { code: "fr", label: "Français" },
];
