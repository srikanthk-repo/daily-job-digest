from datetime import datetime, timezone
import email.message
import html
import os
import smtplib
import feedparser
from jobspy import scrape_jobs
import pandas as pd

# Targeted role queries to search across major portals
SEARCH_QUERIES = [
    "RPA Developer Automation Anywhere",
    "UiPath Developer",
    "Power Automate Developer",
    "Agentic AI Python Developer",
    "Google Apps Script Python",
]

# Major portals to query concurrently
TARGET_SITES = ["linkedin", "indeed", "glassdoor", "google", "naukri"]

# Backup tech RSS feeds
BACKUP_FEEDS = [
    "https://jobicy.com/?feed=job_feed",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
]


def send_email_digest(subject: str, markdown_content: str, html_content: str):
  """Dispatches the daily digest to your inbox."""
  smtp_user = os.environ.get("EMAIL_USERNAME")
  smtp_pass = os.environ.get("EMAIL_PASSWORD")
  recipient = os.environ.get("EMAIL_TO")

  if not all([smtp_user, smtp_pass, recipient]):
    print("Email secrets missing. Skipping email delivery.")
    return

  msg = email.message.EmailMessage()
  msg["Subject"] = subject
  msg["From"] = smtp_user
  msg["To"] = recipient

  msg.set_content(markdown_content)
  msg.add_alternative(html_content, subtype="html")

  try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
      server.login(smtp_user, smtp_pass)
      server.send_message(msg)
    print(f"Successfully sent daily digest to {recipient}")
  except Exception as e:
    print(f"Failed to send email: {e}")


def run():
  all_jobs = []
  seen_links = set()

  # 1. Scrape major job portals (LinkedIn, Indeed, Glassdoor, Google, Naukri)
  for query in SEARCH_QUERIES:
    print(f"Scraping major job boards for: '{query}'...")
    try:
      jobs: pd.DataFrame = scrape_jobs(
          site_name=TARGET_SITES,
          search_term=query,
          location="India",
          results_wanted=10,
          hours_old=72,  # Past 3 days
          country_indeed="India",
          verbose=0,
      )

      if not jobs.empty:
        for _, row in jobs.iterrows():
          link = str(row.get("job_url", "")).strip()
          title = str(row.get("title", "")).strip()
          company = str(row.get("company", "Company")).strip()
          site = str(row.get("site", "Portal")).capitalize()
          loc = str(row.get("location", "India")).strip()
          date_posted = str(row.get("date_posted", "Recent")).strip()

          if link and link != "nan" and link not in seen_links:
            seen_links.add(link)
            all_jobs.append({
                "title": title,
                "company": company,
                "site": site,
                "location": loc,
                "date": date_posted,
                "url": link,
            })
    except Exception as e:
      print(f"Non-fatal error querying portals for '{query}': {e}")

  # 2. Scrape backup RSS feeds for Remote / Python / Automation roles
  for feed_url in BACKUP_FEEDS:
    try:
      feed = feedparser.parse(feed_url)
      for entry in feed.entries:
        link = entry.get("link", "").strip()
        if not link or link in seen_links:
          continue

        title = entry.get("title", "").strip()
        summary = entry.get("summary", "").strip()
        text_corpus = f"{title} {summary}".lower()

        keywords = [
            "rpa",
            "automation",
            "python",
            "agent",
            "langchain",
            "llm",
        ]
        if any(k in text_corpus for k in keywords):
          seen_links.add(link)
          all_jobs.append({
              "title": title,
              "company": entry.get("source", {}).get("title", "Remote Board"),
              "site": "RSS/Direct",
              "location": "Remote / India",
              "date": entry.get("published", "Recent"),
              "url": link,
          })
    except Exception as e:
      print(f"Error parsing feed {feed_url}: {e}")

  today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
  output_filename = f"jobs_{today_str}.md"

  # Quick-launch filtered search URLs
  linkedin_launcher = (
      "https://www.linkedin.com/jobs/search/?"
      "keywords=(RPA%20OR%20UiPath%20OR%20%22Automation%20Anywhere%22%20OR%20%22Agentic%20AI%22%20OR%20Python)&location=India&f_TPR=r86400"
  )
  naukri_launcher = (
      "https://www.naukri.com/rpa-developer-jobs-in-india?"
      "k=rpa%2C%20automation%20anywhere%2C%20uipath%2C%20power%20automate%2C%20python"
  )
  google_launcher = (
      "https://www.google.com/search?q="
      "rpa+developer+or+power+automate+or+agentic+ai+jobs+in+india&ibp=htl;jobs"
  )

  # Markdown format for repository
  md_lines = [
      f"# Daily Job Digest - {today_str}\n\n",
      "> **Target Roles:** RPA (Automation Anywhere, UiPath, Power Automate) | Agentic AI | Vertex AI | Google Apps Script | Python\n\n",
      "### ⚡ 1-Click Live Search Portals\n",
      f"- [Open Live LinkedIn India Roles (Last 24h)]({linkedin_launcher})\n",
      f"- [Open Live Naukri India Matches]({naukri_launcher})\n",
      f"- [Open Live Google Jobs Results]({google_launcher})\n\n",
      f"### 📋 Discovered Listings ({len(all_jobs)} found)\n\n",
  ]

  # HTML format for formatted email
  html_job_items = ""
  for job in all_jobs:
    title_esc = html.escape(job["title"])
    comp_esc = html.escape(job["company"])
    site_esc = html.escape(job["site"])
    loc_esc = html.escape(job["location"])
    date_esc = html.escape(job["date"])
    url = job["url"]

    md_lines.append(
        f"- **[{job['title']}]({url})**\n"
        f"  - **Company:** {job['company']} | **Portal:** {job['site']}\n"
        f"  - **Location:** {job['location']} | **Date:** {job['date']}\n"
    )

    html_job_items += f"""
    <li style="margin-bottom: 12px; padding: 8px; border-bottom: 1px solid #eee;">
      <a href="{url}" style="font-weight: bold; color: #1a73e8; font-size: 15px; text-decoration: none;">{title_esc}</a><br>
      <span style="color: #444;">🏢 {comp_esc} &bull; 🌐 <b>{site_esc}</b> &bull; 📍 {loc_esc}</span><br>
      <small style="color: #888;">🗓 Posted: {date_esc}</small>
    </li>
    """

  if not all_jobs:
    md_lines.append(
        "No direct matches found today across scrapers. Use the 1-Click Search links above.\n"
    )
    html_job_items = (
        "<p>No listings scraped today. Check the 1-click links above.</p>"
    )

  full_md = "".join(md_lines)

  html_template = f"""
  <!DOCTYPE html>
  <html>
  <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #222; max-width: 680px; margin: 0 auto; padding: 15px;">
    <h2 style="color: #1a73e8; margin-bottom: 5px;">🎯 Daily RPA & AI Job Digest ({today_str})</h2>
    <p style="color: #666; font-size: 13px; margin-top: 0;">Targeting: RPA (Automation Anywhere, UiPath, Power Automate), Agentic AI, Apps Script, Python</p>
    
    <div style="background-color: #f1f3f4; padding: 12px; border-radius: 6px; margin: 15px 0;">
      <b>⚡ 1-Click Live Search Portals:</b><br>
      <a href="{linkedin_launcher}" style="color: #0a66c2; margin-right: 12px;">🔗 LinkedIn India (24h)</a>
      <a href="{naukri_launcher}" style="color: #0078db; margin-right: 12px;">🔗 Naukri India</a>
      <a href="{google_launcher}" style="color: #ea4335;">🔗 Google Jobs</a>
    </div>

    <h3>📋 Identified Opportunities ({len(all_jobs)}):</h3>
    <ul style="list-style-type: none; padding-left: 0;">
      {html_job_items}
    </ul>
  </body>
  </html>
  """

  # Save markdown file to repository
  with open(output_filename, "w", encoding="utf-8") as f:
    f.write(full_md)
  print(f"Generated {output_filename} with {len(all_jobs)} jobs.")

  # Send email
  email_subject = (
      f"🎯 Daily Job Digest ({today_str}): {len(all_jobs)} New Opportunities"
  )
  send_email_digest(email_subject, full_md, html_template)


if __name__ == "__main__":
  run()
