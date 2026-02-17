# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Shopify Nano-SRE, please report it responsibly by email to **[security@shopintegrations.com](mailto:security@shopintegrations.com)** rather than using the public issue tracker.

### What to Include

Please include the following information in your report:

- **Description**: A clear explanation of the vulnerability
- **Impact**: Potential impact if the vulnerability is exploited
- **Reproduction Steps**: Steps to reproduce the issue (if applicable)
- **Suggested Fix**: Any ideas you have for addressing the issue (optional)

### Response Timeline

We aim to:

- Acknowledge receipt of your report within **48 hours**
- Provide an estimated timeline for a fix within **5 business days**
- Release a security patch within **30 days** for critical issues
- Keep you informed of our progress

## Security Best Practices

When using Shopify Nano-SRE:

1. **Never commit `.env` files** containing API keys to version control
2. **Use environment variables** for all sensitive configuration
3. **Rotate API keys regularly** and revoke compromised keys immediately
4. **Enable PII redaction** in production via the `--redact` flag
5. **Keep dependencies updated** by running `pip install --upgrade shopify-nano-sre`

## Supported Versions

| Version | Status | Security Updates    |
| ------- | ------ | ------------------- |
| 0.1.x   | Beta   | Until 0.2.0 release |

We recommend always using the latest version of Shopify Nano-SRE.

## Disclosure Policy

Once a security issue is fixed and released, we will:

1. Publish a security advisory on GitHub
2. Mention the fix in release notes
3. Credit the reporter (unless they prefer anonymity)

Thank you for helping keep Shopify Nano-SRE secure.
