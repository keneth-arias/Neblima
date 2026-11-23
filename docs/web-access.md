# Inspect and download web resources

Use Lightpanda first for source pages and web resources. Run it from your
own environment, or ask the data lead to supply verified evidence from a
separate environment. Local checks and continuous integration (CI) run
without a browser session.

1. Open the official page with a bounded timeout, typically 10 to 20
   seconds. Record the requested and final URLs, time in Coordinated
   Universal Time (UTC), status if available, title, and outcome.
2. Inspect the page or accessible tree and resolve the actual resource
   links. A provider landing page returning 200 only verifies access to
   that page.
3. Download an authorized resource with Lightpanda and keep the original
   bytes. Record the source URL, byte count, SHA-256 checksum, observed file
   format, and acquisition time. Leave the file status unknown if the tool
   doesn't expose it. Check that data downloads contain the expected
   format.
4. Record the reason for blocked, missing, authenticated, or timed-out
   resources. Keep the candidate and document an official alternative
   without bypassing the provider's access controls.

Use bounded and reproducible download commands for documented APIs and
large files. Keep the download separate from local conversion. If
Lightpanda fails, document any alternative you use. Follow the work plan
for large downloads, new accounts, and payments. Keep keys, cookies, and
other people's browser sessions out of the repository.
[Acquisition reference](acquisition.md) ·
[Tracked access evidence](../metadata/source-access.json)
