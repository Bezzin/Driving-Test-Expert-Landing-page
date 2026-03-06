export const NAV_ITEMS: import('./types').NavItem[] = [
  {
    label: 'Test Centres',
    href: '/test-centres/',
    children: [
      { label: 'All Test Centres', href: '/test-centres/' },
      { label: 'Easiest Centres', href: '/test-centres/easiest/' },
      { label: 'Hardest Centres', href: '/test-centres/hardest/' },
      { label: 'Pass Rates', href: '/pass-rates/' },
    ],
  },
  { label: 'Our Apps', href: '/test-routes-app' },
  { label: 'About', href: '#about' },
]

export const PLAY_STORE_URL =
  'https://play.google.com/store/apps/details?id=com.drivingtestexpert.testroutesexpert'
export const APP_STORE_URL =
  'https://apps.apple.com/gb/app/test-routes-expert/id6757989639'

export const HOME_PATH = '/'
export const APP_PATH = '/test-routes-app'
export const LEGACY_APP_PATH = '/app'

export const TESTIMONIALS = [
  {
    quote:
      "I'm so grateful for the work you do for everyone not just your students!",
    author: 'Stephanie Rushton',
    source: 'Google review',
    rating: 5,
  },
  {
    quote: "We've found his communication good and the app really useful.",
    author: 'Anita Bates',
    source: 'Google review',
    rating: 5,
  },
  {
    quote:
      'Each lesson was delivered with patience, positivity, and reassurance.',
    author: 'Maudline L',
    source: 'Google review',
    rating: 5,
  },
  {
    quote:
      'Learn everything you need to know in order to pass your driving test right here all in one place.',
    author: 'YouTube audience',
    source: 'YouTube feedback',
    rating: 5,
  },
  {
    quote:
      'Helping learners across the UK with clear practical guidance.',
    author: 'Facebook audience',
    source: 'Facebook feedback',
    rating: 5,
  },
]

export const TRUST_STATS = [
  { value: '350+', label: 'Test centres listed' },
  { value: '4,000+', label: 'Practice routes' },
  { value: '34,000+', label: 'YouTube subscribers' },
  { value: '4M+', label: 'YouTube views' },
]

export const APP_SCREENSHOTS = [
  {
    src: '/app-screenshots/centre-list.png',
    title: 'Choose your test centre quickly',
  },
  {
    src: '/app-screenshots/route-progress.png',
    title: 'Track progress route by route',
  },
  {
    src: '/app-screenshots/route-preview.png',
    title: 'Preview route details before you drive',
  },
  {
    src: '/app-screenshots/navigation-light.png',
    title: 'Turn-by-turn view with clear guidance',
  },
  {
    src: '/app-screenshots/navigation-dark.png',
    title: 'Navigation mode with speed awareness',
  },
]

export const ASSETS = {
  logo: 'https://i.postimg.cc/Jzj70RHs/DTE-Final-Logo.png',
  heroInstructor:
    'https://i.postimg.cc/QdcNCjKC/Gemini-Generated-Image-quvuukquvuukquvu.png',
  reTestBox:
    'https://i.postimg.cc/VkXsvz0c/Gemini-Generated-Image-9p4jmn9p4jmn9p4j.png',
  routesBox:
    'https://i.postimg.cc/c4R9Dzpx/Gemini-Generated-Image-ku3hb0ku3hb0ku3h.png',
  discordBox:
    'https://i.postimg.cc/YCQ20tLC/Gemini-Generated-Image-6w6t5c6w6t5c6w6t.png',
  youtubeBox:
    'https://i.postimg.cc/7ZqBjV45/Gemini-Generated-Image-alymdnalymdnalym-(1).png',
}
