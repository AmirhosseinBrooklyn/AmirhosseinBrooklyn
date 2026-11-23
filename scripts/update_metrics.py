import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from profile_charts import write_charts

API = "https://api.github.com"
SVG = "http://www.w3.org/2000/svg"
METRICS = Path("assets/metrics")
CONTRIBUTION_FIELDS = {
    "Commits": "totalCommitContributions",
    "Issues": "totalIssueContributions",
    "PRs": "totalPullRequestContributions",
    "Reviews": "totalPullRequestReviewContributions",
}


# Collect public statistics

def github(path, token, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Brooklyn-profile-metrics",
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    request = Request(f"{API}{path}", data=body, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response), response.headers.get("Link", "")


def public_repositories(user, token):
    page = 1
    repositories = []
    while True:
        batch, links = github(f"/users/{quote(user)}/repos?type=owner&per_page=100&page={page}", token)
        repositories.extend(repo for repo in batch if not repo["private"])
        if 'rel="next"' not in links:
            return repositories
        page += 1


def recent_contributions(user, token, now):
    fields = " ".join(CONTRIBUTION_FIELDS.values())
    query = (
        "query($user: String!, $from: DateTime!, $to: DateTime!) {"
        " user(login: $user) { contributionsCollection(from: $from, to: $to) { "
        f"{fields}"
        " } } }"
    )
    variables = {
        "user": user,
        "from": (now - timedelta(days=365)).isoformat(timespec="seconds"),
        "to": now.isoformat(timespec="seconds"),
    }
    data, _ = github("/graphql", token, {"query": query, "variables": variables})
    if data.get("errors"):
        raise RuntimeError(f"GitHub rejected the contributions query: {data['errors'][0]['message']}")
    collection = data["data"]["user"]["contributionsCollection"]
    return {label: collection[field] for label, field in CONTRIBUTION_FIELDS.items()}


def profile_views(user):
    query = urlencode({"username": user, "label": "Views", "style": "flat"})
    request = Request(f"https://komarev.com/ghpvc/?{query}",
                      headers={"User-Agent": "Brooklyn-profile-metrics"})
    with urlopen(request, timeout=20) as response:
        root = ET.parse(response).getroot()
    for item in reversed(root.findall(".//{*}text")):
        value = (item.text or "").strip().replace(",", "")
        if re.fullmatch(r"[0-9]+", value):
            return int(value)
    raise ValueError("The view counter returned no count")


def collect(user, token):
    now = datetime.now(timezone.utc)
    profile, _ = github(f"/users/{quote(user)}", token)
    repositories = public_repositories(user, token)
    originals = [repo for repo in repositories if not repo["fork"]]
    languages = Counter()
    for repo in originals:
        if repo["size"] > 0:
            sizes, _ = github(f"/repos/{quote(user)}/{quote(repo['name'])}/languages", token)
            languages.update(sizes)
    contributions = recent_contributions(user, token, now)
    try:
        views = profile_views(user)
    except (URLError, ValueError, ET.ParseError, TimeoutError) as error:
        print(f"::warning::Preserving the last view count because the counter could not be read: {type(error).__name__}")
        views = None
    return {
        "date": now.date().isoformat(),
        "followers": profile["followers"],
        "stars": sum(repo["stargazers_count"] for repo in repositories),
        "views": views,
        "public_repos": len(repositories),
        "original_repos": len(originals),
        "original_stars": sum(repo["stargazers_count"] for repo in originals),
        "languages": dict(languages),
        "contributions": contributions,
    }


# Refresh approved SVGs

def update_badge(path, count):
    if count is None:
        return
    root = ET.parse(path).getroot()
    title = root.find(f"{{{SVG}}}title")
    label, value = root.findall(f"{{{SVG}}}text")
    outer = root.find(f"{{{SVG}}}rect")
    digits = f"{count:,}"
    value_width = sum(4 if char == "," else 8 for char in digits)
    width = int(value.get("x")) + value_width + 10
    title.text = f"{label.text}: {digits}"
    root.set("aria-label", title.text)
    root.set("width", str(width))
    root.set("viewBox", f"0 0 {width} 26")
    outer.set("width", str(width - 1))
    value.text = digits
    value.set("textLength", str(value_width))
    xml = ET.tostring(root, encoding="unicode") + "\n"
    path.write_text(xml, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    data = collect(os.environ["PROFILE_OWNER"], os.environ["GH_TOKEN"])
    ET.register_namespace("", SVG)
    for name in ("followers", "stars", "views"):
        update_badge(METRICS / f"{name}-pill.svg", data[name])
    write_charts(METRICS, data)
    args.summary.write_text(json.dumps(data), encoding="utf-8")


if __name__ == "__main__":
    main()
