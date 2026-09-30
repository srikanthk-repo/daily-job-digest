from datetime import datetime, timezone
import os
import feedparser

# Verified public job RSS feeds that do not require API keys or login sessions
FEEDS = [
    "https://jobicy.com/?feed=job_feed",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://remotive.com/remote-jobs/feed",
]

# Keywords matching your target roles and technical skills
KEYWORDS = [
    "python",
    "automation",
    "developer",
    "data engineer",
    "rpa",
    "software engineer",
]

# Location filters
LOCATIONS = ["india", "remote", "anywhere", "worldwide", "apac"]


def run():
  matches = []
  seen_links = set()

  for feed_url in FEEDS:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
      link = entry.get("link", "")
      if link in seen_links:
        continue

      title = entry.get("title", "").strip()
      summary = entry.get("summary", "").strip()
      text_corpus = f"{title} {summary}".lower()

      has_keyword = any(k.lower() in text_corpus for k in KEYWORDS)
      has_location = any(loc.lower() in text_corpus for loc in LOCATIONS)

      if has_keyword and has_location:
        seen_links.add(link)
        pub_date = entry.get("published", "Recently Posted")
        matches.append(
            f"- **[{title}]({link})**\n  - Source: {entry.get('source', {}).get('title', 'Public Feed')}\n  - Date: {pub_date}\n"
        )

  today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
  output_filename = f"jobs_{today_str}.md"

  with open(output_filename, "w", encoding="utf-8") as f:
    f.write(f"# Daily Job Digest - {today_str}\n\n")
    f.write(
        f"> Found **{len(matches)}** open roles matching keywords: `{', '.join(KEYWORDS)}`\n\n"
    )

    if matches:
      f.write("## Verified Listings\n\n")
      f.writelines(matches)
    else:
      f.write(
          "No new matching roles identified today. Check back tomorrow.\n"
      )

  print(f"Successfully generated {output_filename} with {len(matches)} jobs.")


if __name__ == "__main__":
  run()
