export type Video = {
  id: string;
  file: string;
  poster?: string;
  project: string;
  title: string;
  caption?: string;
  tiktok_url?: string;
  github_issue_url?: string;
  generated_at: string;
};

export type EngagementCounts = {
  views: number;
  likes: number;
  comment_count: number;
};

export type EngagementSnapshot = EngagementCounts & {
  liked_by_session: boolean;
};
