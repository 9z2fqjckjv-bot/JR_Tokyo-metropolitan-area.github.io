const data = window.RAILWAY_DATA;
const groups = data.groups;
const routes = data.routes;

const serviceText = (services) => (services.length ? services.join("、") : "通過のみ");
const byId = (id) => document.getElementById(id);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child == null) continue;
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function routeDiagram(route) {
  return el("div", { class: "diagram", role: "list", "aria-label": `${route.name}の駅順` },
    route.stations.map((station) => el("div", { class: "station-node", role: "listitem", title: `${station.name}（${station.code}）` }, [
      el("span", { class: "station-dot", "aria-hidden": "true" }),
      el("span", { class: "station-code" }, [station.code]),
      el("span", { class: "station-name-label" }, [station.name.replace(/駅$/, "")]),
    ]))
  );
}

function serviceStopChips(stations, service) {
  const stops = stations.filter((station) => station.services.includes(service));
  if (!stops.length) return el("p", { class: "empty-note" }, ["該当する停車駅はありません"]);
  return el("div", { class: "stop-chip-row" }, stops.map((station) =>
    el("span", { class: "stop-chip" }, [
      el("strong", {}, [station.name]),
      el("small", {}, [station.code]),
    ])
  ));
}

function routeCard(route) {
  const card = el("article", { class: "route-card" });
  card.append(
    el("header", {}, [
      el("div", {}, [
        el("h3", {}, [route.name]),
        el("p", {}, [`${route.stationCount}駅 / ${route.services.length}種別`]),
      ]),
      el("a", { class: "button secondary", href: route.page }, ["路線ページ"]),
    ]),
    el("div", { class: "route-meta" }, route.services.map((service) => el("span", { class: "pill" }, [service]))),
    routeDiagram(route)
  );
  return card;
}

function renderOverview() {
  const stats = byId("overviewStats");
  if (!stats) return;
  const stationNames = new Set(routes.flatMap((route) => route.stations.map((station) => station.name)));
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
  if (!cards) return;
  groups.forEach((group) => {
    const groupRoutes = routes.filter((route) => route.group === group.id);
    cards.append(el("a", { class: "group-card", href: group.page }, [
      el("h3", {}, [group.title]),
      el("p", {}, [`${groupRoutes.length}路線、${groupRoutes.reduce((sum, route) => sum + route.stationCount, 0)}駅を掲載`]),
    ]));
  });
}

function renderGroupRoutes() {
  const list = byId("routeList");
  if (!list) return;
  const groupId = list.dataset.group;
  routes.filter((route) => route.group === groupId).forEach((route) => list.append(routeCard(route)));
}

function renderRouteDetail() {
  const root = byId("routeDetail");
  if (!root || !window.SELECTED_ROUTE_ID) return;
  const route = routes.find((item) => item.id === window.SELECTED_ROUTE_ID);
  if (!route) return;
  const group = groups.find((item) => item.id === route.group);

  root.append(
    el("div", { class: "section-heading" }, [
      el("div", {}, [el("p", { class: "eyebrow" }, ["Route"]), el("h2", {}, [route.name])]),
      el("a", { class: "button secondary", href: `../${group.page}` }, ["路線図へ戻る"]),
    ]),
    el("div", { class: "route-summary" }, [
      el("div", { class: "summary-item" }, [el("span", {}, ["駅数"]), el("strong", {}, [String(route.stationCount)])]),
      el("div", { class: "summary-item" }, [el("span", {}, ["種別数"]), el("strong", {}, [String(route.services.length)])]),
      el("div", { class: "summary-item wide" }, [
        el("span", {}, ["運行種別"]),
        el("div", { class: "route-meta" }, route.services.map((service) => el("span", { class: "pill" }, [service]))),
      ]),
    ]),
    el("h2", { class: "block-title" }, ["駅順図"]),
    routeDiagram(route),
    el("h2", { class: "block-title" }, ["種別ごとの停車駅一覧"]),
    el("div", { class: "service-panels" }, route.services.map((service) => {
      const stops = route.stations.filter((station) => station.services.includes(service));
      return el("section", { class: "service-panel" }, [
        el("header", {}, [
          el("h3", {}, [service]),
          el("span", { class: "pill" }, [`${stops.length}駅停車`]),
        ]),
        serviceStopChips(route.stations, service),
        el("details", { class: "service-details" }, [
          el("summary", {}, ["表形式で見る"]),
          el("table", { class: "service-table" }, [
            el("thead", {}, [el("tr", {}, [el("th", {}, ["駅ナンバリング"]), el("th", {}, ["駅名"])])]),
            el("tbody", {}, stops.map((station) => el("tr", {}, [
              el("td", {}, [station.code]),
              el("td", {}, [station.name]),
            ]))),
          ]),
        ]),
      ]);
    }))
  );
}

function buildStationIndex() {
  const index = new Map();
  routes.forEach((route) => {
    route.stations.forEach((station) => {
      if (!index.has(station.name)) index.set(station.name, []);
      index.get(station.name).push({ route, station });
    });
  });
  return [...index.entries()].sort(([a], [b]) => a.localeCompare(b, "ja"));
}

function uniqueServices() {
  const set = new Set();
  routes.forEach((route) => route.services.forEach((service) => set.add(service)));
  return [...set].sort((a, b) => a.localeCompare(b, "ja"));
}

function renderStations() {
  const input = byId("stationSearch");
  const count = byId("stationCount");
  const results = byId("stationResults");
  const groupFilter = byId("groupFilter");
  const serviceFilter = byId("serviceFilter");
  const empty = byId("stationEmpty");
  if (!input || !results) return;

  const stationIndex = buildStationIndex();

  if (groupFilter) {
    groups.forEach((group) => {
      groupFilter.append(el("option", { value: group.id }, [group.title]));
    });
  }
  if (serviceFilter) {
    uniqueServices().forEach((service) => {
      serviceFilter.append(el("option", { value: service }, [service]));
    });
  }

  function draw() {
    const query = input.value.trim().toLowerCase();
    const groupId = groupFilter ? groupFilter.value : "";
    const service = serviceFilter ? serviceFilter.value : "";

    const matched = stationIndex.filter(([name, entries]) => {
      const filteredEntries = entries.filter(({ route, station }) => {
        if (groupId && route.group !== groupId) return false;
        if (service && !station.services.includes(service)) return false;
        return true;
      });
      if (!filteredEntries.length) return false;
      if (!query) {
        entries._filtered = filteredEntries;
        return true;
      }
      const haystack = filteredEntries.map(({ route, station }) =>
        [name, station.code, route.name, serviceText(station.services)].join(" ").toLowerCase()
      ).join(" ");
      const ok = haystack.includes(query) || name.toLowerCase().includes(query);
      if (ok) entries._filtered = filteredEntries;
      return ok;
    });

    results.replaceChildren();
    count.textContent = `${matched.length}駅を表示中`;
    if (empty) empty.hidden = matched.length > 0;

    matched.forEach(([name, entries]) => {
      const shown = entries._filtered || entries;
      const lines = [...new Set(shown.map(({ route }) => route.name))];
      const codes = [...new Set(shown.map(({ station }) => station.code))];
      const services = [...new Set(shown.flatMap(({ station }) => station.services))];

      const card = el("article", { class: "station-card enriched" }, [
        el("header", { class: "station-card-head" }, [
          el("div", {}, [
            el("p", { class: "eyebrow" }, ["Station"]),
            el("h3", {}, [name]),
          ]),
          el("div", { class: "numbering-badges" }, codes.map((code) => el("span", { class: "numbering-badge" }, [code]))),
        ]),
        el("dl", { class: "station-facts" }, [
          el("div", {}, [el("dt", {}, ["乗り入れ路線"]), el("dd", {}, [lines.join("、")])]),
          el("div", {}, [el("dt", {}, ["駅ナンバリング"]), el("dd", {}, [codes.join(" / ")])]),
          el("div", {}, [el("dt", {}, ["停車種別"]), el("dd", {}, [
            services.length
              ? el("div", { class: "route-meta" }, services.map((item) => el("span", { class: "service-pill" }, [item])))
              : "通過のみ",
          ])]),
        ]),
        el("div", { class: "station-lines" }, shown.map(({ route, station }) => el("div", { class: "station-line" }, [
          el("div", { class: "station-line-top" }, [
            el("strong", {}, [route.name]),
            el("a", { class: "text-link compact-link", href: route.page }, ["路線詳細"]),
          ]),
          el("p", {}, [`この路線のナンバリング: ${station.code}`]),
          el("p", {}, [`この路線の停車種別: ${serviceText(station.services)}`]),
        ]))),
      ]);
      results.append(card);
    });
  }

  input.addEventListener("input", draw);
  if (groupFilter) groupFilter.addEventListener("change", draw);
  if (serviceFilter) serviceFilter.addEventListener("change", draw);
  draw();
}

renderOverview();
renderGroupRoutes();
renderRouteDetail();
renderStations();
