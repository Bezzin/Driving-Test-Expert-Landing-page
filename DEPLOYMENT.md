# Domain Setup Guide for drivingtestexpert.com

## Quick Setup Options

### Option 1: Vercel (Recommended - Easiest)

1. **Deploy to Vercel:**
   - Push your code to GitHub (if not already)
   - Go to [vercel.com](https://vercel.com) and sign in with GitHub
   - Click "Add New Project" → Import your repository
   - Vercel auto-detects Vite - no configuration needed!
   - Click "Deploy"

2. **Add Your Domain:**
   - Go to your project → **Settings** → **Domains**
   - Add `drivingtestexpert.com`
   - Add `www.drivingtestexpert.com` (optional but recommended)
   - Vercel will show you DNS records to add

3. **Configure DNS at Your Domain Registrar:**
   - Go to where you bought the domain (GoDaddy, Namecheap, etc.)
   - Add these DNS records:
     - **A Record:** `@` → `76.76.21.21`
     - **CNAME Record:** `www` → `cname.vercel-dns.com`
   - Wait 24-48 hours for DNS to propagate

### Option 2: Netlify

1. **Deploy to Netlify:**
   - Push your code to GitHub
   - Go to [netlify.com](https://netlify.com) → "Add new site" → "Import an existing project"
   - Connect your GitHub repository
   - Build settings:
     - **Build command:** `npm run build`
     - **Publish directory:** `dist`
   - Click "Deploy site"

2. **Add Your Domain:**
   - Go to **Site settings** → **Domain management** → **Add custom domain**
   - Enter `drivingtestexpert.com`
   - Netlify will provide DNS records

3. **Configure DNS:**
   - Add the DNS records Netlify provides at your domain registrar

### Option 3: Cloudflare Pages

1. **Deploy to Cloudflare:**
   - Push your code to GitHub
   - Cloudflare Dashboard → **Pages** → **Create a project**
   - Connect your repository
   - Build settings:
     - **Build command:** `npm run build`
     - **Build output directory:** `dist`
   - Deploy

2. **Add Your Domain:**
   - If your domain is already on Cloudflare: It auto-configures!
   - If not: Add DNS records as shown in Cloudflare Pages

## DNS Configuration (General)

At your domain registrar, you'll typically need:

- **A Record** (for root domain):
  - Name: `@` or blank
  - Value: (IP provided by your hosting platform)
  
- **CNAME Record** (for www subdomain):
  - Name: `www`
  - Value: (CNAME provided by your hosting platform)

## Important Notes

- DNS changes can take 24-48 hours to propagate globally
- Make sure your site is deployed and working before adding the domain
- SSL/HTTPS is usually automatic on these platforms
- Keep your hosting platform's DNS records updated if they change

## Need Help?

If you're unsure which platform to use:
- **Vercel**: Best for React apps, easiest setup
- **Netlify**: Great free tier, good for static sites
- **Cloudflare Pages**: Best if you already use Cloudflare, fastest CDN

