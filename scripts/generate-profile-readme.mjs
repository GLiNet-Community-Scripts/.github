import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const ORG = process.env.GITHUB_ORG || "GLiNet-Community-Scripts";
const OUTPUT_FILE = process.env.OUTPUT_FILE || path.join("profile", "README.md");
const TEMPLATE_FILE =
  process.env.TEMPLATE_FILE || path.join("profile", "README.template.md");
const API_BASE_URL = process.env.GITHUB_API_BASE_URL || "https://api.github.com";

function formatDate(value) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Berlin",
  }).format(new Date(value));
}

function formatRelativeDate(value) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeZone: "Europe/Berlin",
  }).format(new Date(value));
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-GB").format(value);
}

function escapeTableCell(value) {
  return String(value ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ").trim();
}

function getOriginalRepo(repo) {
  return repo.parent || repo.source || repo;
}

function getDisplayedStars(repo) {
  return getOriginalRepo(repo).stargazers_count ?? repo.stargazers_count ?? 0;
}

async function fetchRepos() {
  const repos = [];
  const headers = {
    Accept: "application/vnd.github+json",
    "User-Agent": `${ORG}-profile-generator`,
  };

  if (process.env.GITHUB_TOKEN) {
    headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  }

  async function fetchJson(url) {
    let response;
    try {
      response = await fetch(url, { headers });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`GitHub API request could not be completed: ${message}`);
    }

    if (!response.ok) {
      const message = await response.text();
      throw new Error(
        `GitHub API request failed (${response.status} ${response.statusText}): ${message}`,
      );
    }

    return response.json();
  }

  for (let page = 1; page <= 10; page += 1) {
    const url = new URL(`${API_BASE_URL}/orgs/${ORG}/repos`);
    url.searchParams.set("type", "public");
    url.searchParams.set("sort", "updated");
    url.searchParams.set("per_page", "100");
    url.searchParams.set("page", String(page));

    const pageRepos = await fetchJson(url);
    repos.push(...pageRepos);

    if (pageRepos.length < 100) {
      break;
    }
  }

  const publicRepos = repos
    .filter((repo) => !repo.private && repo.name !== ".github")
    .sort((a, b) => a.name.localeCompare(b.name, "en"));

  return Promise.all(
    publicRepos.map(async (repo) => {
      if (!repo.fork) {
        return repo;
      }

      const detailsUrl = `${API_BASE_URL}/repos/${repo.full_name}`;
      const details = await fetchJson(detailsUrl);
      return { ...repo, parent: details.parent, source: details.source };
    }),
  );
}

function buildRepoTable(repos) {
  if (repos.length === 0) {
    return "_No public repositories were found._";
  }

  const lines = [
    "| Repository | Description | Stars | Author | Original URL | Last Updated |",
    "| --- | --- | ---: | --- | --- | --- |",
  ];

  for (const repo of repos) {
    const badges = [];
    if (repo.archived) {
      badges.push("archived");
    }

    const name = [`[${repo.name}](${repo.html_url})`, badges.length ? `(${badges.join(", ")})` : ""]
      .join(" ")
      .trim();
    const originalRepo = getOriginalRepo(repo);
    const author = originalRepo.owner?.login || repo.owner?.login || "-";
    const originalUrl = originalRepo.html_url || repo.html_url;
    const originalLabel = originalRepo.full_name || "Original repo";
    const stars = getDisplayedStars(repo);

    lines.push(
      `| ${escapeTableCell(name)} | ${escapeTableCell(repo.description || "No description provided")} | ${formatNumber(stars)} | ${escapeTableCell(author)} | ${escapeTableCell(`[${originalLabel}](${originalUrl})`)} | ${escapeTableCell(formatRelativeDate(repo.updated_at))} |`,
    );
  }

  return lines.join("\n");
}

async function main() {
  const [template, repos] = await Promise.all([
    readFile(TEMPLATE_FILE, "utf8"),
    fetchRepos(),
  ]);

  const totalStars = repos.reduce(
    (sum, repo) => sum + getDisplayedStars(repo),
    0,
  );

  const readme = template
    .replaceAll("{{REPO_COUNT}}", formatNumber(repos.length))
    .replaceAll("{{TOTAL_STARS}}", formatNumber(totalStars))
    .replaceAll("{{GENERATED_AT}}", formatDate(new Date().toISOString()))
    .replace("{{REPO_TABLE}}", buildRepoTable(repos));

  await mkdir(path.dirname(OUTPUT_FILE), { recursive: true });
  await writeFile(OUTPUT_FILE, `${readme.trim()}\n`, "utf8");
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
