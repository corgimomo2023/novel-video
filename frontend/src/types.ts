export interface ProjectSummary {
  id: string; title: string; source_text: string; status: string; created_at: string; updated_at: string;
  shot_count: number; completed_shots: number
}
export interface Character { id: string; project_id: string; name: string; description: string; voice: string; reference_url?: string }
export interface Shot { id: string; project_id: string; sequence: number; title: string; prompt: string; dialogue: string; duration_seconds: number; engine: string; status: string; output_url?: string }
export interface Project extends Omit<ProjectSummary, 'shot_count' | 'completed_shots'> { characters: Character[]; shots: Shot[] }
export interface Job { id: string; project_id: string; shot_id: string; status: string; provider: string; progress: number; error?: string; cost_usd: number; created_at: string; started_at?: string; finished_at?: string; shot_title: string; project_title: string; engine: string }
export interface DashboardData { projects: number; shots: number; completed: number; queued: number; recent_jobs: Job[] }
export interface GPUStatus { provider: string; configured: boolean; status: string; gpu_type: string; mode: string; note: string }
