# Security policy

## Supported versions

Security fixes are provided for the latest release and the default
branch. Older releases are not supported. Upgrade before reporting
an issue that may already be fixed.

## Reporting a vulnerability

Do not open a public issue, pull request, or discussion for a suspected
vulnerability.

Use either private channel:

- **GitHub Security Advisories.** Open a private report from this
  repository's Security tab, **Report a vulnerability**. This is the
  preferred channel.
- **Email.** `jechenmailman@gmail.com`, with a subject line that begins
  with `[SECURITY]`.

Include the affected version, platform, impact, and steps to reproduce.
Do not attach credentials, tokens, or unredacted logs.

The maintainers aim to acknowledge a report within 5 business days, and
to coordinate a fix and disclosure within 90 days. There is no bug-bounty
promise.

## Operational notes

API keys come from the environment or from local application settings, not
from this repository.

Publisher detection compares the end of the host name. A name that merely
ends with a publisher's domain is not a reliable allow decision, and the
download path can open that host in a browser. Do not point downloads at a
URL list you do not trust, and do not attach a signed-in browser profile to
that path.
