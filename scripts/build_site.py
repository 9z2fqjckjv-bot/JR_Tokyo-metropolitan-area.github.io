#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
NS = {"k": "http://www.opengis.net/kml/2.2"}

SOURCES = [
    {
        "id": "tokyo",
        "title": "東京鉄道路線図",
        "description": "東京鉄道の路線図",
        "kmz": ROOT / "東京鉄道路線図.kmz",
        "page": "tokyo.html",
    },
    {
        "id": "loop",
        "title": "東京環状鉄道路線図",
        "description": "東京環状鉄道の路線図",
        "kmz": ROOT / "東京環状鉄道路線図.kmz",
        "page": "loop.html",
    },
]


def text(node: ET.Element | None, default: str = "") -> str:
    if node is None or node.text is None:
        return default
    return node.text.strip()


def href_from_local_kmz(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        with zf.open("doc.kml") as fp:
            root = ET.parse(fp).getroot()
    href = text(root.find(".//k:NetworkLink/k:Link/k:href", NS))
    if not href:
        raise ValueError(f"{path.name} にNetworkLinkのhrefが見つかりません")
    return href


def download_kml(url: str) -> ET.Element:
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = response.read()
    with tempfile.TemporaryDirectory() as tmpdir:
        kmz_path = Path(tmpdir) / "source.kmz"
        kmz_path.write_bytes(payload)
        with zipfile.ZipFile(kmz_path) as zf:
            with zf.open("doc.kml") as fp:
                return ET.parse(fp).getroot()


def station_from_placemark(pm: ET.Element) -> dict[str, object]:
    code = text(pm.find("k:name", NS))
    address = text(pm.find("k:address", NS))
    fields: dict[str, str] = {}
    for item in pm.findall("k:ExtendedData/k:Data", NS):
        key = item.attrib.get("name", "").strip()
        value = text(item.find("k:value", NS))
        if key:
            fields[key] = value
    station_name = fields.get("駅名") or address or code
    services = [name for name, value in fields.items() if name != "駅名" and value]
    all_services = [name for name in fields if name != "駅名"]
    return {
        "code": code,
        "name": station_name,
        "services": services,
        "allServices": all_services,
    }


def parse_source(source: dict[str, object]) -> dict[str, object]:
    href = href_from_local_kmz(source["kmz"])  # type: ignore[arg-type]
    root = download_kml(href)
    routes = []
    for index, folder in enumerate(root.findall(".//k:Document/k:Folder", NS), start=1):
        stations = [station_from_placemark(pm) for pm in folder.findall("k:Placemark", NS)]
        if not stations:
            continue
        service_order: list[str] = []
        for station in stations:
            for service in station["allServices"]:  # type: ignore[index]
                if service not in service_order:
                    service_order.append(service)
        route_id = f"{source['id']}-{index:02d}"
        routes.append(
            {
                "id": route_id,
                "name": text(folder.find("k:name", NS), f"路線{index}"),
                "group": source["id"],
                "stationCount": len(stations),
                "services": service_order,
                "stations": stations,
                "page": f"routes/{route_id}.html",
            }
        )
    return {
        "id": source["id"],
        "title": source["title"],
        "description": source["description"],
        "mapUrl": href,
        "page": source["page"],
        "routes": routes,
    }


def page_shell(title: str, page: str, body: str, base: str = "") -> str:
    nav = [
        ("概要", "index.html"),
        ("東京鉄道路線図", "tokyo.html"),
        ("東京環状鉄道路線図", "loop.html"),
        ("駅一覧", "stations.html"),
        ("サイトリンク", "links.html"),
    ]
    nav_parts = []
    for label, href in nav:
        current = ' aria-current="page"' if page == href else ""
        nav_parts.append(f'<a href="{base}{href}"{current}>{label}</a>')
    nav_html = "".join(nav_parts)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | JR首都圏</title>
  <link rel="stylesheet" href="{base}assets/styles.css">
</head>
<body data-page="{html.escape(page)}">
  <header class="site-header">
    <a class="brand" href="{base}index.html">
      <span class="brand-mark">JR</span>
      <span><strong>JR首都圏</strong><small>架空鉄道会社サイト</small></span>
    </a>
    <nav class="site-nav" aria-label="主要ナビゲーション">{nav_html}</nav>
  </header>
  <main>{body}</main>
  <footer class="site-footer">
    <p>このサイトは架空の鉄道会社「JR首都圏」を紹介するWebサイトです。</p>
    <p>作成者: zuyasi</p>
  </footer>
  <script src="{base}assets/data.js"></script>
  <script src="{base}assets/app.js"></script>
</body>
</html>
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_static_pages(data: dict[str, object]) -> None:
    write_text(
        ROOT / "index.html",
        page_shell(
            "概要",
            "index.html",
            """
    <section class="hero">
      <p class="eyebrow">Fictional Railway Company</p>
      <h1>東京圏を結ぶ架空鉄道路線ポータル</h1>
      <p>リポジトリ内の「東京鉄道路線図」「東京環状鉄道路線図」をもとに、各路線の図式化、種別ごとの停車駅、駅検索をまとめました。</p>
      <div class="hero-actions">
        <a class="button" href="tokyo.html">東京鉄道路線図を見る</a>
        <a class="button secondary" href="stations.html">駅を検索する</a>
      </div>
    </section>
    <section class="notice">
      <strong>ご案内</strong>
      <p>このサイトは架空の鉄道会社の情報サイトです。実在の鉄道会社・路線とは関係ありません。</p>
    </section>
    <section class="section">
      <div class="section-heading">
        <p class="eyebrow">Overview</p>
        <h2>収録データ</h2>
      </div>
      <div id="overviewStats" class="stats-grid"></div>
    </section>
    <section class="section">
      <div class="section-heading">
        <p class="eyebrow">Routes</p>
        <h2>路線グループ</h2>
      </div>
      <div id="groupCards" class="card-grid"></div>
    </section>
""",
        ),
    )

    for group in data["groups"]:  # type: ignore[index]
        group_id = group["id"]
        write_text(
            ROOT / group["page"],
            page_shell(
                group["title"],
                group["page"],
                f"""
    <section class="page-hero compact">
      <p class="eyebrow">Route Map</p>
      <h1>{html.escape(group["title"])}</h1>
      <p>{html.escape(group["description"])}を、路線ごとの停車駅図として掲載しています。</p>
      <a class="text-link" href="{html.escape(group["mapUrl"])}" target="_blank" rel="noopener">元のGoogleマップKMLを開く</a>
    </section>
    <section class="section">
      <div class="section-heading">
        <p class="eyebrow">Diagram</p>
        <h2>各路線の図式化</h2>
      </div>
      <div id="routeList" data-group="{html.escape(group_id)}" class="route-list"></div>
    </section>
""",
            ),
        )

    write_text(
        ROOT / "stations.html",
        page_shell(
            "駅一覧",
            "stations.html",
            """
    <section class="page-hero compact">
      <p class="eyebrow">Station Index</p>
      <h1>駅一覧・停車種別検索</h1>
      <p>駅名を入力すると、その駅が含まれる路線と停車する種別を確認できます。</p>
    </section>
    <section class="section">
      <label class="search-label" for="stationSearch">駅名検索</label>
      <input id="stationSearch" class="search-input" type="search" placeholder="例: 東京、新宿、宇都宮">
      <div id="stationCount" class="result-count"></div>
      <div id="stationResults" class="station-results"></div>
    </section>
""",
        ),
    )

    write_text(
        ROOT / "links.html",
        page_shell(
            "サイトリンク",
            "links.html",
            """
    <section class="page-hero compact">
      <p class="eyebrow">Site Links</p>
      <h1>サイトリンク</h1>
      <p>関連する外部サイトへのリンクです。</p>
    </section>
    <section class="section link-grid">
      <a class="link-card" href="https://9z2fqjckjv-bot.github.io/zuyasi.github.io/main/index.html">
        <span>zuyasiのWebサイト</span>
        <small>https://9z2fqjckjv-bot.github.io/zuyasi.github.io/main/index.html</small>
      </a>
      <a class="link-card" href="https://9z2fqjckjv-bot.github.io/nanndemoya.github.io/">
        <span>何でも屋概要</span>
        <small>https://9z2fqjckjv-bot.github.io/nanndemoya.github.io/</small>
      </a>
    </section>
""",
        ),
    )

    routes_dir = ROOT / "routes"
    if routes_dir.exists():
        shutil.rmtree(routes_dir)
    routes_dir.mkdir()
    for route in data["routes"]:  # type: ignore[index]
        write_text(
            ROOT / route["page"],
            page_shell(
                route["name"],
                "",
                f"""
    <script>window.SELECTED_ROUTE_ID = {json.dumps(route["id"], ensure_ascii=False)};</script>
    <section class="page-hero compact">
      <p class="eyebrow">Route Detail</p>
      <h1>{html.escape(route["name"])}</h1>
      <p>路線名と、種別ごとの停車駅一覧を掲載しています。</p>
    </section>
    <section id="routeDetail" class="section"></section>
""",
                base="../",
            ),
        )


CSS = r"""
:root {
  --bg: #f4f7fb;
  --surface: #ffffff;
  --surface-soft: #eef5ff;
  --text: #162033;
  --muted: #62708a;
  --line: #dbe4f0;
  --primary: #0b67d1;
  --primary-dark: #074a99;
  --accent: #12a6a6;
  --shadow: 0 18px 50px rgba(11, 49, 99, 0.12);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
  color: var(--text);
  background: linear-gradient(135deg, #e9f4ff 0%, var(--bg) 38%, #ffffff 100%);
  line-height: 1.7;
}

a { color: inherit; }

.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px clamp(18px, 4vw, 56px);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--line);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 15px;
  color: #fff;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  font-weight: 800;
  letter-spacing: .04em;
}

.brand small {
  display: block;
  color: var(--muted);
  font-size: 12px;
}

.site-nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.site-nav a {
  padding: 8px 12px;
  border-radius: 999px;
  color: var(--muted);
  text-decoration: none;
  font-weight: 700;
  font-size: 14px;
}

.site-nav a:hover,
.site-nav a[aria-current="page"] {
  color: var(--primary-dark);
  background: var(--surface-soft);
}

main {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 42px 0 72px;
}

.hero,
.page-hero,
.notice,
.section {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: var(--shadow);
}

.hero {
  padding: clamp(36px, 7vw, 82px);
  background:
    radial-gradient(circle at 86% 12%, rgba(18, 166, 166, .17), transparent 28%),
    linear-gradient(135deg, rgba(11, 103, 209, .12), rgba(255, 255, 255, .96));
}

.hero h1,
.page-hero h1 {
  margin: 6px 0 18px;
  font-size: clamp(32px, 6vw, 64px);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.hero p,
.page-hero p {
  max-width: 760px;
  color: var(--muted);
  font-size: 18px;
}

.compact {
  padding: clamp(28px, 5vw, 52px);
}

.eyebrow {
  margin: 0;
  color: var(--primary);
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 28px;
}

.button,
.text-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 46px;
  padding: 10px 18px;
  border-radius: 999px;
  background: var(--primary);
  color: #fff;
  text-decoration: none;
  font-weight: 800;
}

.button.secondary {
  color: var(--primary-dark);
  background: var(--surface);
  border: 1px solid var(--line);
}

.text-link {
  min-height: auto;
  margin-top: 8px;
  color: var(--primary-dark);
  background: var(--surface-soft);
}

.notice,
.section {
  margin-top: 24px;
  padding: clamp(22px, 4vw, 36px);
}

.notice {
  border-left: 8px solid var(--accent);
}

.notice p { margin-bottom: 0; }

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 22px;
}

.section-heading h2 {
  margin: 4px 0 0;
  font-size: clamp(24px, 4vw, 38px);
}

.stats-grid,
.card-grid,
.link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}

.stat-card,
.group-card,
.link-card,
.station-card,
.route-card {
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
}

.stat-card strong {
  display: block;
  font-size: 34px;
  color: var(--primary-dark);
}

.group-card,
.link-card {
  display: block;
  text-decoration: none;
}

.group-card h3,
.route-card h3,
.station-card h3 {
  margin: 0 0 8px;
}

.group-card p,
.route-card p,
.station-card p,
.link-card small {
  color: var(--muted);
}

.route-list {
  display: grid;
  gap: 18px;
}

.route-card header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.route-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill,
.service-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--primary-dark);
  font-size: 13px;
  font-weight: 800;
}

.diagram {
  display: flex;
  align-items: stretch;
  gap: 0;
  overflow-x: auto;
  padding: 10px 0 4px;
}

.station-node {
  position: relative;
  min-width: 74px;
  padding-top: 30px;
  text-align: center;
  color: var(--muted);
  font-size: 12px;
}

.station-node::before {
  content: "";
  position: absolute;
  top: 11px;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary), var(--accent));
}

.station-node:first-child::before { left: 50%; }
.station-node:last-child::before { right: 50%; }

.station-dot {
  position: absolute;
  top: 3px;
  left: 50%;
  z-index: 1;
  width: 20px;
  height: 20px;
  transform: translateX(-50%);
  border: 4px solid var(--primary);
  border-radius: 50%;
  background: #fff;
}

.station-code {
  display: block;
  color: var(--primary-dark);
  font-weight: 800;
}

.service-table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 18px;
}

.service-table th,
.service-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

.service-table th {
  background: var(--surface-soft);
  color: var(--primary-dark);
}

.search-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 800;
}

.search-input {
  width: 100%;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 18px;
  font: inherit;
  background: #fff;
}

.result-count {
  margin: 14px 0;
  color: var(--muted);
  font-weight: 700;
}

.station-results {
  display: grid;
  gap: 12px;
}

.station-lines {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.station-line {
  padding: 12px;
  border-radius: 16px;
  background: var(--surface-soft);
}

.site-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px 24px;
  padding: 28px;
  color: var(--muted);
  border-top: 1px solid var(--line);
  background: #fff;
}

.site-footer p { margin: 0; }

@media (max-width: 760px) {
  .site-header {
    position: static;
    align-items: flex-start;
    flex-direction: column;
  }

  .site-nav {
    justify-content: flex-start;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
"""


APP_JS = r"""
const data = window.RAILWAY_DATA;
const groups = data.groups;
const routes = data.routes;

const serviceText = (services) => services.length ? services.join("、") : "通過";
const byId = (id) => document.getElementById(id);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

function routeDiagram(route) {
  return el("div", { class: "diagram", role: "list", "aria-label": `${route.name}の駅順` },
    route.stations.map(station => el("div", { class: "station-node", role: "listitem" }, [
      el("span", { class: "station-dot", "aria-hidden": "true" }),
      el("span", { class: "station-code" }, [station.code]),
      document.createTextNode(station.name.replace(/駅$/, ""))
    ]))
  );
}

function routeCard(route) {
  const card = el("article", { class: "route-card" });
  card.append(
    el("header", {}, [
      el("div", {}, [
        el("h3", {}, [route.name]),
        el("p", {}, [`${route.stationCount}駅 / ${route.services.length}種別`])
      ]),
      el("a", { class: "button secondary", href: route.page }, ["路線ページ"])
    ]),
    el("div", { class: "route-meta" }, route.services.map(service => el("span", { class: "pill" }, [service]))),
    routeDiagram(route)
  );
  return card;
}

function renderOverview() {
  const stats = byId("overviewStats");
  if (!stats) return;
  const stationNames = new Set(routes.flatMap(route => route.stations.map(station => station.name)));
  const totalStations = routes.reduce((sum, route) => sum + route.stationCount, 0);
  [
    ["路線グループ", groups.length],
    ["路線数", routes.length],
    ["延べ駅数", totalStations],
    ["駅名数", stationNames.size],
  ].forEach(([label, value]) => {
    stats.append(el("div", { class: "stat-card" }, [el("strong", {}, [String(value)]), el("span", {}, [label])]));
  });

  const cards = byId("groupCards");
  groups.forEach(group => {
    const groupRoutes = routes.filter(route => route.group === group.id);
    cards.append(el("a", { class: "group-card", href: group.page }, [
      el("h3", {}, [group.title]),
      el("p", {}, [`${groupRoutes.length}路線、${groupRoutes.reduce((sum, route) => sum + route.stationCount, 0)}駅を掲載`])
    ]));
  });
}

function renderGroupRoutes() {
  const list = byId("routeList");
  if (!list) return;
  const groupId = list.dataset.group;
  routes.filter(route => route.group === groupId).forEach(route => list.append(routeCard(route)));
}

function renderRouteDetail() {
  const root = byId("routeDetail");
  if (!root || !window.SELECTED_ROUTE_ID) return;
  const route = routes.find(item => item.id === window.SELECTED_ROUTE_ID);
  if (!route) return;
  root.append(
    el("div", { class: "section-heading" }, [
      el("div", {}, [el("p", { class: "eyebrow" }, ["Route"]), el("h2", {}, [route.name])]),
      el("a", { class: "button secondary", href: `../${groups.find(group => group.id === route.group).page}` }, ["路線図へ戻る"])
    ]),
    routeDiagram(route),
    el("h2", {}, ["種別ごとの停車駅一覧"]),
    el("table", { class: "service-table" }, [
      el("thead", {}, [el("tr", {}, [el("th", {}, ["種別"]), el("th", {}, ["停車駅"])])]),
      el("tbody", {}, route.services.map(service => {
        const stops = route.stations.filter(station => station.services.includes(service)).map(station => `${station.name}（${station.code}）`);
        return el("tr", {}, [el("th", {}, [service]), el("td", {}, [stops.join("、") || "該当なし"])]);
      }))
    ])
  );
}

function buildStationIndex() {
  const index = new Map();
  routes.forEach(route => {
    route.stations.forEach(station => {
      if (!index.has(station.name)) index.set(station.name, []);
      index.get(station.name).push({ route, station });
    });
  });
  return [...index.entries()].sort(([a], [b]) => a.localeCompare(b, "ja"));
}

function renderStations() {
  const input = byId("stationSearch");
  const count = byId("stationCount");
  const results = byId("stationResults");
  if (!input || !results) return;
  const stationIndex = buildStationIndex();

  function draw() {
    const query = input.value.trim().toLowerCase();
    const matched = stationIndex.filter(([name]) => name.toLowerCase().includes(query));
    results.replaceChildren();
    count.textContent = `${matched.length}駅を表示中`;
    matched.forEach(([name, entries]) => {
      const card = el("article", { class: "station-card" }, [
        el("h3", {}, [name]),
        el("div", { class: "station-lines" }, entries.map(({ route, station }) => el("div", { class: "station-line" }, [
          el("strong", {}, [route.name]),
          el("p", {}, [`駅番号: ${station.code} / 停車種別: ${serviceText(station.services)}`])
        ])))
      ]);
      results.append(card);
    });
  }

  input.addEventListener("input", draw);
  draw();
}

renderOverview();
renderGroupRoutes();
renderRouteDetail();
renderStations();
"""


def main() -> None:
    groups = [parse_source(source) for source in SOURCES]
    routes = [route for group in groups for route in group["routes"]]  # type: ignore[index]
    data = {"groups": groups, "routes": routes}
    write_text(ROOT / "assets" / "styles.css", CSS.strip() + "\n")
    write_text(ROOT / "assets" / "app.js", APP_JS.strip() + "\n")
    write_text(
        ROOT / "assets" / "data.js",
        "window.RAILWAY_DATA = "
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
    )
    render_static_pages(data)


if __name__ == "__main__":
    main()
