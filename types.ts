export interface NavItem {
  label: string;
  href: string;
}

export interface Feature {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  image: string; // URL or placeholder path
  reverse?: boolean;
  cta?: string;
  isGlassOrange?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}
