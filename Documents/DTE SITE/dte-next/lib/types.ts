export interface NavItem {
  label: string
  href: string
}

export interface Feature {
  id: string
  title: string
  subtitle: string
  description: string
  image: string
  reverse?: boolean
  cta?: string
  ctaLink?: string
  isGlassOrange?: boolean
}

export interface ChatMessage {
  role: 'user' | 'model'
  text: string
}
