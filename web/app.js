"use strict";

const RANKERS = {
  bm25: { name: "BM25", desc: "Keyword matching" },
  dense: { name: "Dense", desc: "Embedding similarity (bge-base-en-v1.5)" },
  hybrid: { name: "Hybrid", desc: "Rank fusion of BM25 and dense" },
};
const DOCS = { ai_act: "AI Act", mdr: "MDR", ivdr: "IVDR", gdpr: "GDPR" };
const CATEGORY_TAGS = { cross_regulation: "cross-regulation", out_of_scope: "out of scope" };
const TOP_K = 5;
const SNIPPET_CHARS = 240;

const form = document.getElementById("search-form");
const query = document.getElementById("query");
const rankerSelect = document.getElementById("ranker");
const submit = document.getElementById("submit");
const charCount = document.getElementById("char-count");
const statusLine = document.getElementById("status");
const results = document.getElementById("results");

let available = Object.keys(RANKERS);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("error", isError);
}

function snippet(text) {
  const body = text.replace(/^#+\s.*$/gm, "").replace(/\s+/g, " ").trim();
  return body.length > SNIPPET_CHARS ? body.slice(0, SNIPPET_CHARS).trimEnd() + "…" : body;
}

async function loadHealth() {
  try {
    const health = await (await fetch("health")).json();
    available = health.rankers.filter((r) => r in RANKERS);
    for (const option of rankerSelect.options) {
      if (option.value !== "compare") option.disabled = !available.includes(option.value);
    }
    document.getElementById("corpus-info").textContent =
      `${health.chunks.toLocaleString("en")} passages indexed. Rankers: ` +
      available.map((r) => RANKERS[r].name).join(", ") + ".";
  } catch {
    setStatus("The search service is not reachable right now.", true);
  }
}

async function loadExamples() {
  const list = document.getElementById("examples");
  try {
    const examples = await (await fetch("examples")).json();
    for (const example of examples) {
      const button = el("button", "", example.question);
      button.type = "button";
      const tag = CATEGORY_TAGS[example.category];
      if (tag) button.append(el("span", "example-tag", tag));
      button.addEventListener("click", () => {
        query.value = example.question;
        updateCount();
        form.requestSubmit();
      });
      const item = el("li");
      item.append(button);
      list.append(item);
    }
  } catch {
    list.closest("section").hidden = true;
  }
  if (!list.children.length) list.closest("section").hidden = true;
}

async function search(text, ranker) {
  const response = await fetch("search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: text, ranker, k: TOP_K }),
  });
  if (response.status === 429) {
    const wait = response.headers.get("Retry-After");
    throw new Error(`Too many searches. Please wait ${wait || "a minute"} seconds and try again.`);
  }
  if (!response.ok) throw new Error("The search failed. Please try a different question.");
  return response.json();
}

function renderHit(hit) {
  const item = el("li", "hit");
  item.dataset.key = `${hit.doc_id}|${hit.article}`;

  const head = el("div", "hit-head");
  head.append(el("span", "hit-rank", `${hit.rank}.`));
  const doc = el("span", "hit-doc", DOCS[hit.doc_id] || hit.doc_id);
  if (hit.source.title) doc.title = hit.source.title;
  head.append(doc, el("span", "hit-article", hit.article));
  item.append(head);

  item.append(el("p", "hit-citation", hit.citation));
  item.append(el("p", "hit-snippet", snippet(hit.text)));

  const details = el("details");
  details.append(el("summary", "", "Full passage"), el("pre", "", hit.text));
  item.append(details);

  const meta = [hit.source.version, hit.source.retrieved && `retrieved ${hit.source.retrieved}`];
  const metaText = meta.filter(Boolean).join(", ");
  if (metaText) item.append(el("p", "hit-meta", metaText));
  return item;
}

function renderColumn(ranker, hits) {
  const column = el("section", "column");
  column.append(el("h2", "", RANKERS[ranker].name), el("p", "column-desc", RANKERS[ranker].desc));
  if (!hits.length) {
    column.append(el("p", "empty", "No matching passages."));
    return column;
  }
  const list = el("ol");
  for (const hit of hits) list.append(renderHit(hit));
  column.append(list);
  return column;
}

function highlightMatches(event) {
  const hit = event.target.closest(".hit");
  const key = event.type === "mouseover" && hit ? hit.dataset.key : null;
  for (const node of results.querySelectorAll(".hit")) {
    node.classList.toggle("match", key !== null && node.dataset.key === key);
  }
}

function updateCount() {
  charCount.textContent = `${query.value.length} / ${query.maxLength}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = query.value.trim();
  if (!text) return;
  const choice = rankerSelect.value;
  const rankers = choice === "compare" ? available : [choice];

  submit.disabled = true;
  setStatus("Searching…");
  try {
    const responses = await Promise.all(rankers.map((r) => search(text, r)));
    results.replaceChildren(...responses.map((r) => renderColumn(r.ranker, r.hits)));
    setStatus(
      rankers.length > 1
        ? "Hover over a result to see where the same article ranks in the other columns."
        : "",
    );
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submit.disabled = false;
  }
});

query.addEventListener("input", updateCount);
query.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
results.addEventListener("mouseover", highlightMatches);
results.addEventListener("mouseleave", highlightMatches);

loadHealth();
loadExamples();
