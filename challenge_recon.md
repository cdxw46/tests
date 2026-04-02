# Excom Challenge Reconnaissance

## Target: www.excom.es

### Web Properties Found:
- **www.excom.es** - Main site (Symfony/PHP, Apache, OpenResty)
  - Admin panel at `/login` (email + password + CSRF)
  - Routes found in JS: `/admin/dashboard`, `/admin/products/`, `/admin/categories/`, `/admin/sliders/`, `/admin/benefits/`, `/admin/landing/`, `/admin/landings`, `/callme-generate`, `/home/front`
  - AJAX endpoints: `/ajax/search-rate/`, `/ajax/search-rate-initial/`
  - Client area: redirects to `clientesexcom.ispgestion.com` (Yii Framework)
  
- **vfy.excom.es** (ExVerify) - CodeIgniter 4, Apache/2.4.65 (Debian), INSPINIA 4.2.0 template
  - Shows "Enlace Inválido" - needs specific verification link
  - All routes return same SPA page
  - `.env` file accessible (but example/commented out)

- **185.228.126.16** - Kasm Workspaces (nginx/1.22.1)
- **api-provisioner.excom.es** - nginx/1.29.1, redirects to Google
- **tmola.excom.es** - nginx/1.29.1, redirects to Google
- **tarifas.excom.es** - nginx, Site Not Configured
- **www.promos.excom.es** - Empty HTML page

### Challenge Goal:
- Find 75+ leads (fictional data)
- One lead contains the root flag
- Need to extract leads with params: phone, IBAN, etc.
- Submit leads file to verify flag

### Technologies:
- Symfony (main site)
- CodeIgniter 4 (ExVerify)
- Yii Framework (ISP client portal)
- nginx, Apache, OpenResty
