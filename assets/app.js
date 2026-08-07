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
