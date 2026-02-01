<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/drive/18gvdOLmYzqgKUNHll6aitpjENZrCj3ZC

## Run Locally

**Prerequisites:** Node.js 18+

### Quick Start

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Set up environment variables:**

   ```bash
   # Copy the example file
   cp .env.example .env.local

   # Edit .env.local and add your API keys
   # Replace placeholder values with actual keys
   ```

3. **Validate environment variables:**

   ```bash
   npm run validate:env
   ```

4. **Run the development server:**

   ```bash
   npm run dev
   ```

5. **Open your browser:**
   Navigate to `http://localhost:3000`

### Environment Variables

The application requires certain environment variables to function correctly. All client-side environment variables must be prefixed with `VITE_` to be exposed to the browser.

#### Required Variables

- **`VITE_GEMINI_API_KEY`** - API key for Google Gemini AI integration
  - Get your key from: https://makersuite.google.com/app/apikey
  - This key is embedded in the production bundle and visible to users
  - Consider using API key restrictions in Google Cloud Console

#### Configuration Files

- **`.env.example`** - Template file with all required variables (committed to git)
- **`.env.local`** - Your local environment variables (ignored by git)
- **`.env`** - Alternative environment file (ignored by git)

Priority order: `.env.local` > `.env` > `.env.example`

#### Validation

Before building for production, validate your environment variables:

```bash
npm run validate:env
```

This script checks that:

- All required variables are set
- Values are not placeholders
- Configuration is ready for deployment

#### Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit `.env` or `.env.local` files** - They contain sensitive API keys
2. **API keys in frontend are visible to users** - Only use keys safe for client-side exposure
3. **Use API key restrictions** - Configure allowed domains/IPs in Google Cloud Console
4. **Rotate keys regularly** - Update API keys periodically for security
5. **Check `.gitignore`** - Ensure `.env*` files are excluded from version control

### Build Commands

```bash
# Standard build (no validation)
npm run build

# Safe build (validates environment variables first)
npm run build:safe

# Build and verify output
npm run build:verify

# Validate environment only
npm run validate:env

# Verify build output only
npm run verify
```

### Deployment

For AWS deployment, see the root-level `deploy.sh` script. The deployment process:

1. Validates environment variables
2. Builds the production bundle
3. Uploads to S3
4. Configures CloudFront CDN
5. Invalidates cache

```bash
# From project root
./deploy.sh
```
