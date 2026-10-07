const CART_KEY = "rid-cart";
const STATES = [
  ["NSW", "New South Wales"],
  ["VIC", "Victoria"],
  ["QLD", "Queensland"],
  ["SA", "South Australia"],
  ["WA", "Western Australia"],
  ["TAS", "Tasmania"],
  ["NT", "Northern Territory"],
  ["ACT", "Australian Capital Territory"],
];

const state = { catalog: null, error: "" };

function el(tag, props = {}, kids = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null || value === false) continue;
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const kid of [].concat(kids)) {
    if (kid == null || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

function money(cents) {
  const dollars = cents / 100;
  const text = Number.isInteger(dollars) ? String(dollars) : dollars.toFixed(2);
  return `AU$${text}`;
}

function cart() {
  try {
    const saved = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function saveCart(lines) {
  localStorage.setItem(CART_KEY, JSON.stringify(lines));
  const count = document.getElementById("cart-count");
  if (count) count.textContent = String(lines.reduce((sum, line) => sum + line.qty, 0));
}

function cartCount() {
  return cart().reduce((sum, line) => sum + line.qty, 0);
}

async function api(path, body) {
  const response = await fetch(path, body ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } : undefined);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The shop could not complete that.");
  return data;
}

function designBySlug(slug) {
  return state.catalog.designs.find((item) => item.slug === slug);
}

function fabricRow(design, fabricId) {
  return design.fabrics.find((item) => item.id === fabricId);
}

function unitCents(design, fabricId, size) {
  const fabric = fabricRow(design, fabricId);
  if (!fabric) return 0;
  return size === "2XL" ? fabric.price_2xl_cents : fabric.price_cents;
}

function art(design) {
  if (design.image) {
    return el("div", { class: `art art-${design.slug}` }, [
      el("img", { src: design.image, alt: "" }),
    ]);
  }
  return el("div", { class: `art art-${design.slug}`, "aria-hidden": "true" }, [
    el("span", { class: "a" }),
    el("span", { class: "b" }),
    el("span", { class: "c" }),
  ]);
}

function etsyAnchor(catalog, label, href) {
  return el("a", {
    href: href || catalog.etsy_listing_url,
    target: "_blank",
    rel: "noopener noreferrer",
  }, label);
}

function parseRoute() {
  const url = new URL(location.href);
  const path = url.pathname;
  const product = path.match(/^\/product\/([a-z0-9-]+)$/);
  const order = path.match(/^\/order\/(RID-[A-F0-9]{8})$/i);
  if (path === "/" || path === "") return { name: "home" };
  if (path === "/shop") return { name: "shop", series: url.searchParams.get("series") || "all" };
  if (product) {
    return {
      name: "product",
      slug: product[1],
      fabric: url.searchParams.get("fabric") || "poly",
      size: url.searchParams.get("size") || "",
    };
  }
  if (path === "/cart") return { name: "cart" };
  if (path === "/checkout") return { name: "checkout", cancelled: url.searchParams.get("cancelled") === "1" };
  if (order) return { name: "order", id: order[1].toUpperCase(), session: url.searchParams.get("session_id") || "" };
  if (path === "/shipping") return { name: "shipping" };
  if (path === "/about") return { name: "about" };
  return { name: "missing" };
}

function navigate(href) {
  const url = new URL(href, location.origin);
  history.pushState({}, "", url.pathname + url.search + url.hash);
  render().then(() => {
    if (!url.hash) window.scrollTo(0, 0);
  });
}

function setTitle(title, description) {
  document.title = title;
  const meta = document.querySelector('meta[name="description"]');
  if (meta && description) meta.setAttribute("content", description);
}

function setRobots(mode) {
  const meta = document.querySelector('meta[name="robots"]');
  if (!meta) return;
  meta.setAttribute("content", mode === "stripe" || mode === "payid" ? "index,follow" : "noindex");
}

function chrome(catalog) {
  saveCart(cart());
  setRobots(catalog.checkout.mode);
  const banner = document.getElementById("demo-banner");
  banner.replaceChildren();
  if (catalog.checkout.mode === "demo") {
    banner.hidden = false;
    const lead = catalog.checkout.demo_lead;
    const emphasis = catalog.checkout.demo_emphasis;
    const chunks = lead.split(emphasis);
    const kids = [];
    if (chunks.length === 2) {
      kids.push(chunks[0], el("strong", {}, emphasis), chunks[1], " ");
    } else {
      kids.push(lead, " ");
    }
    const tail = catalog.checkout.demo_tail;
    const marker = "Etsy shop";
    const split = tail.split(marker);
    if (split.length === 2) {
      kids.push(split[0], etsyAnchor(catalog, marker), split[1]);
    } else {
      kids.push(tail);
    }
    banner.append(el("p", {}, kids));
  } else {
    banner.hidden = true;
  }
  const footer = document.getElementById("site-footer");
  footer.replaceChildren(
    ...catalog.footer.map((line) => el("span", {}, line)),
    etsyAnchor(catalog, catalog.etsy_link_label),
  );
  footer.lastElementChild.classList.add("etsy-link");
}

function pageHead(title, paragraphs) {
  return el("header", { class: "page-head wrap" }, [
    el("h1", {}, title),
    ...paragraphs.filter(Boolean).map((text) => el("p", { class: "lede" }, text)),
  ]);
}

function renderHome(catalog) {
  setTitle(catalog.seo.title, catalog.seo.meta);
  const series = el("section", { class: "series wrap", id: "series" }, catalog.series.map((item) => (
    el("a", { href: `/shop?series=${item.id}` }, item.label)
  )));
  const grid = el("section", { class: "grid wrap" }, catalog.designs.map(card));
  return [
    el("section", { class: "hero wrap" }, [
      el("img", { class: "hero-banner", src: "/brand/banner.png", alt: "Rogers Inc Designs" }),
      el("p", { class: "kicker" }, catalog.shop.collection),
      el("h1", {}, catalog.home.headline),
      el("p", { class: "sub" }, catalog.home.sub),
      el("div", { class: "actions" }, [
        el("a", { class: "btn", href: "/shop" }, catalog.home.cta_primary),
        el("a", { class: "btn btn-ghost", href: "/#series" }, catalog.home.cta_secondary),
      ]),
      el("p", { class: "alt" }, catalog.home.alt),
    ]),
    series,
    grid,
  ];
}

function card(design) {
  const poly = fabricRow(design, "poly");
  const cotton = fabricRow(design, "cotton");
  return el("a", { class: "card", href: `/product/${design.slug}` }, [
    art(design),
    el("p", { class: "series-name" }, design.series_name),
    el("h2", {}, design.name),
    el("p", { class: "hook" }, design.hook),
    el("p", { class: "meta" }, `Polyester ${money(poly.price_cents)} · Cotton ${money(cotton.price_cents)}`),
  ]);
}

function renderShop(catalog, route) {
  setTitle("Shop — Rogers Inc Designs", catalog.seo.meta);
  const known = catalog.series.some((item) => item.id === route.series);
  const series = route.series === "all" || !known ? "all" : route.series;
  const designs = series === "all" ? catalog.designs : catalog.designs.filter((item) => item.series === series);
  const filters = el("nav", { class: "filters wrap", "aria-label": "Series" }, [
    el("a", { href: "/shop", "aria-current": series === "all" ? "true" : null }, "All"),
    ...catalog.series.map((item) => el("a", {
      href: `/shop?series=${item.id}`,
      "aria-current": series === item.id ? "true" : null,
    }, item.label)),
  ]);
  const empty = designs.length ? null : el("p", { class: "empty wrap" }, "That series is not in the shop.");
  return [
    pageHead("Shop", [catalog.shop.intro, catalog.shop.fabrics, catalog.shop.collection]),
    filters,
    empty,
    el("section", { class: "grid wrap" }, designs.map(card)),
  ];
}

function renderProduct(catalog, route) {
  const design = designBySlug(route.slug);
  if (!design) return [pageHead("Not in the shop", ["That tee is not in the Rogers Inc Designs shop."])];
  setTitle(`${design.name} — Rogers Inc Designs`, `${design.hook} Free shipping in Australia.`);
  const fabric = design.fabrics.some((item) => item.id === route.fabric) ? route.fabric : "poly";
  const size = catalog.sizes.includes(route.size) ? route.size : "";
  const selected = fabricRow(design, fabric);
  const price = unitCents(design, fabric, size || "M");
  const shown = size ? price : selected.price_cents;

  const fabricPills = el("div", { class: "pills" }, design.fabrics.map((item) => {
    const cents = size === "2XL" ? item.price_2xl_cents : item.price_cents;
    return el("label", {}, [
      el("input", { type: "radio", name: "fabric", value: item.id, checked: item.id === fabric ? "checked" : null }),
      `${item.label} · ${money(cents)}`,
    ]);
  }));
  const sizePills = el("div", { class: "pills" }, catalog.sizes.map((item) => (
    el("label", {}, [
      el("input", { type: "radio", name: "size", value: item, checked: item === size ? "checked" : null }),
      item,
    ])
  )));
  const form = el("form", { id: "buy" }, [
    el("fieldset", { class: "choice" }, [el("legend", {}, "Fabric"), fabricPills]),
    el("fieldset", { class: "choice" }, [el("legend", {}, "Size"), sizePills]),
    el("p", { class: "price", id: "price", "aria-live": "polite" }, money(shown)),
    el("p", { class: "note" }, size ? (size === "2XL" ? "2XL is +AU$4." : catalog.footer[2]) : "Select a size. 2XL is +AU$4."),
    el("label", { class: "qty" }, ["Quantity", el("input", { name: "qty", type: "number", min: "1", max: "4", value: "1" })]),
    el("button", { class: "btn", type: "submit" }, "Add to cart"),
    el("p", { class: "added", id: "added", "aria-live": "polite" }, ""),
  ]);
  form.addEventListener("change", (event) => {
    if (event.target.name === "qty") return;
    const nextFabric = new FormData(form).get("fabric");
    const nextSize = new FormData(form).get("size") || "";
    const params = new URLSearchParams({ fabric: nextFabric });
    if (nextSize) params.set("size", nextSize);
    history.replaceState({}, "", `/product/${design.slug}?${params}`);
    render();
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const chosen = data.get("size");
    const added = document.getElementById("added");
    if (!chosen) {
      added.textContent = "Choose a size from XS to 2XL.";
      return;
    }
    const qty = Math.min(4, Math.max(1, Number(data.get("qty")) || 1));
    const lines = cart();
    const existing = lines.find((line) => line.slug === design.slug && line.fabric === fabric && line.size === chosen);
    if (existing) existing.qty = Math.min(4, existing.qty + qty);
    else lines.push({ slug: design.slug, fabric, size: chosen, qty });
    saveCart(lines);
    added.textContent = "Added to cart. No payment taken yet.";
  });

  const etsy = selected.etsy_url ? el("p", { class: "note" }, [
    etsyAnchor(catalog, catalog.etsy_link_label, selected.etsy_url),
  ]) : null;

  return [el("article", { class: "product wrap" }, [
    art(design),
    el("div", {}, [
      el("p", { class: "series-name" }, design.series_name),
      el("h1", {}, design.name),
      el("p", { class: "hook" }, design.hook),
      el("p", { class: "blurb" }, design.blurbs[fabric]),
      form,
      el("p", { class: "note" }, [
        catalog.size_note.split("size guide")[0],
        el("a", { href: "/shipping#size-guide" }, "size guide"),
        catalog.size_note.split("size guide")[1] || "",
      ]),
      etsy,
    ]),
  ])];
}

function renderCart(catalog) {
  setTitle("Cart — Rogers Inc Designs", catalog.seo.meta);
  const lines = cart();
  if (!lines.length) {
    return [
      pageHead("Cart", []),
      el("p", { class: "empty wrap" }, [
        "Your cart is empty. ",
        el("a", { href: "/shop" }, catalog.home.cta_primary),
        ".",
      ]),
    ];
  }
  const list = el("div", { class: "cart wrap", id: "cart-lines" }, [el("p", {}, "Checking prices…")]);
  api("/api/quote", { lines }).then((quote) => {
    list.replaceChildren(...quote.lines.map((line) => lineRow(line)), totals(quote, catalog));
  }).catch((error) => {
    list.replaceChildren(el("p", { class: "alert" }, error.message));
  });
  return [pageHead("Cart", []), list];
}

function lineRow(line) {
  return el("article", { class: "line" }, [
    el("div", {}, [
      el("p", { class: "series-name" }, line.series_name),
      el("h2", {}, line.name),
      el("p", { class: "note" }, `${line.fabric_label} · ${line.size}`),
    ]),
    el("p", {}, money(line.line_cents)),
    el("div", { class: "row-actions" }, [
      el("button", { class: "icon-btn", type: "button", "data-qty": "-1", "data-key": lineKey(line), "aria-label": "Fewer" }, "−"),
      el("span", {}, String(line.qty)),
      el("button", { class: "icon-btn", type: "button", "data-qty": "1", "data-key": lineKey(line), "aria-label": "More" }, "+"),
      el("button", { class: "linkish", type: "button", "data-remove": lineKey(line) }, "Remove"),
    ]),
  ]);
}

function lineKey(line) {
  return `${line.slug}|${line.fabric}|${line.size}`;
}

function totals(quote, catalog) {
  return el("div", { class: "totals" }, [
    el("p", {}, catalog.footer[2]),
    el("p", {}, catalog.footer[1]),
    el("strong", {}, money(quote.total_cents)),
    el("a", { class: "btn", href: "/checkout" }, "Checkout"),
  ]);
}

function renderCheckout(catalog, route) {
  setTitle("Checkout — Rogers Inc Designs", catalog.seo.meta);
  const mode = catalog.checkout.mode;
  const lines = cart();
  if (!lines.length) {
    return [pageHead("Checkout", []), el("p", { class: "empty wrap" }, "Your cart is empty.")];
  }
  const noticeClass = mode === "demo" ? "notice notice-demo" : "notice";
  const summary = el("div", { id: "summary" }, [el("p", {}, "Checking prices…")]);
  const error = el("p", { class: "alert", id: "checkout-error" }, "");
  const buttonLabel = {
    demo: "Place a demo order — no charge, no print",
    stripe: "Continue to secure card payment",
    payid: "Place order and show PayID",
    off: "Payments are not switched on",
  }[mode];
  const form = el("form", { class: "fields", id: "checkout-form" }, [
    field("Name", "name", "text", true),
    field("Email", "email", "email", true),
    field("Phone (optional)", "phone", "tel", false),
    field("Street address", "line1", "text", true),
    field("Address line 2 (optional)", "line2", "text", false),
    el("div", { class: "grid-2" }, [
      field("Suburb", "suburb", "text", true),
      stateField(),
    ]),
    el("div", { class: "grid-2" }, [
      field("Postcode", "postcode", "text", true),
      el("label", {}, ["Country", el("input", { value: "Australia", disabled: "disabled" })]),
    ]),
    el("button", { class: "btn", type: "submit", disabled: mode === "off" ? "disabled" : null }, buttonLabel),
  ]);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const customer = Object.fromEntries(new FormData(form).entries());
    try {
      const order = await api("/api/checkout", { lines: cart(), customer });
      if (order.url) {
        location.href = order.url;
        return;
      }
      saveCart([]);
      navigate(`/order/${order.id}`);
    } catch (err) {
      error.textContent = err.message;
      button.disabled = mode === "off";
    }
  });
  api("/api/quote", { lines }).then((quote) => {
    summary.replaceChildren(...quote.lines.map((line) => (
      el("p", {}, `${line.qty} × ${line.name} · ${line.fabric_label} · ${line.size} · ${money(line.line_cents)}`)
    )), el("strong", {}, money(quote.total_cents)));
  }).catch((err) => {
    summary.replaceChildren(el("p", { class: "alert" }, err.message));
  });
  const cancelled = route.cancelled ? el("p", { class: "alert" }, "Card payment was cancelled. No charge was taken and nothing was sent to print.") : null;
  return [
    pageHead("Checkout", [catalog.checkout.international]),
    el("section", { class: "checkout wrap" }, [
      cancelled,
      el("div", { class: noticeClass }, noticeBody(catalog, mode)),
      summary,
      error,
      form,
    ]),
  ];
}

function noticeBody(catalog, mode) {
  if (mode === "demo") {
    return [
      el("strong", { class: "stamp" }, "NO CHARGE · NO PRINT"),
      el("p", {}, [
        catalog.checkout.demo_lead.split(catalog.checkout.demo_emphasis)[0],
        el("strong", {}, catalog.checkout.demo_emphasis),
        catalog.checkout.demo_lead.split(catalog.checkout.demo_emphasis)[1] || "",
      ]),
    ];
  }
  return [el("p", {}, catalog.checkout[mode] || catalog.checkout.off)];
}

function field(label, name, type, required) {
  const input = el("input", {
    name,
    type,
    autocomplete: autocompleteFor(name),
    required: required ? "required" : null,
    maxlength: name === "postcode" ? "4" : "120",
    inputmode: name === "postcode" ? "numeric" : null,
  });
  return el("label", {}, [label, input]);
}

function autocompleteFor(name) {
  return {
    name: "name",
    email: "email",
    phone: "tel",
    line1: "address-line1",
    line2: "address-line2",
    suburb: "address-level2",
    postcode: "postal-code",
  }[name] || "on";
}

function stateField() {
  const select = el("select", { name: "state", autocomplete: "address-level1", required: "required" }, [
    el("option", { value: "" }, "State"),
    ...STATES.map(([code, label]) => el("option", { value: code }, label)),
  ]);
  return el("label", {}, ["State", select]);
}

async function renderOrder(catalog, route) {
  setTitle("Order — Rogers Inc Designs", catalog.seo.meta);
  const box = el("section", { class: "order wrap" }, [el("p", {}, "Loading the order…")]);
  const query = route.session ? `?session_id=${encodeURIComponent(route.session)}` : "";
  try {
    const order = await api(`/api/orders/${route.id}${query}`);
    const kids = [el("h1", {}, order.id)];
    if (order.mode === "demo") {
      kids.push(el("p", { class: "stamp" }, "NO CHARGE · NO PRINT"));
      kids.push(el("p", {}, order.notice.text));
    } else if (order.mode === "payid" && !order.payment_taken) {
      kids.push(el("p", {}, order.notice.text));
      kids.push(el("p", {}, `Pay ${money(order.total_cents)} to PayID ${order.payid} (${order.payid_name}).`));
      kids.push(el("p", {}, `Reference ${order.reference}. The tee is not sent to print until this payment clears.`));
    } else if (order.payment_taken) {
      kids.push(el("p", {}, "Payment received."));
      kids.push(el("p", {}, catalog.delivery));
    } else {
      kids.push(el("p", {}, order.notice.text));
    }
    kids.push(...order.lines.map((line) => (
      el("p", {}, `${line.qty} × ${line.listing_name} · ${line.fabric_label} · ${line.size} · ${money(line.line_cents)}`)
    )));
    kids.push(el("strong", {}, money(order.total_cents)));
    kids.push(el("p", { class: "note" }, `${order.customer.name}, ${order.customer.suburb} ${order.customer.state} ${order.customer.postcode}`));
    kids.push(el("p", { class: "note" }, order.created_brisbane));
    box.replaceChildren(...kids);
  } catch (error) {
    box.replaceChildren(el("p", { class: "alert" }, error.message));
  }
  return [box];
}

function renderShipping(catalog) {
  setTitle("Shipping — Rogers Inc Designs", catalog.seo.meta);
  return [el("article", { class: "prose wrap" }, [
    el("header", { class: "page-head" }, [el("h1", {}, "Shipping and returns")]),
    el("h2", {}, "Shipping"),
    el("p", { class: "lede" }, catalog.shipping),
    el("h2", {}, "Delivery"),
    el("p", { class: "lede" }, catalog.delivery),
    el("h2", { id: "size-guide" }, "Size guide"),
    el("p", { class: "lede" }, catalog.size_note),
    el("p", { class: "lede" }, catalog.size_chart_gap),
    el("h2", {}, "Returns"),
    el("p", { class: "lede" }, catalog.returns),
    el("p", { class: "lede" }, catalog.returns_contact_gap),
  ])];
}

function renderAbout(catalog) {
  setTitle("About — Rogers Inc Designs", catalog.seo.meta);
  const parts = catalog.about.split("Elemental Wood");
  const about = parts.length === 2
    ? [parts[0], etsyAnchor(catalog, "Elemental Wood"), parts[1]]
    : [catalog.about];
  return [el("article", { class: "prose wrap" }, [
    el("header", { class: "page-head" }, [el("h1", {}, "Rogers Inc Designs")]),
    el("p", { class: "lede" }, about),
    el("p", { class: "lede" }, catalog.shop.collection),
  ])];
}

function renderMissing() {
  setTitle("Not found — Rogers Inc Designs");
  return [pageHead("That page is not here", []), el("p", { class: "empty wrap" }, [el("a", { href: "/shop" }, "Shop the tees")])];
}

async function render() {
  const app = document.getElementById("app");
  const route = parseRoute();
  if (!state.catalog) {
    app.replaceChildren(el("p", { class: "loading" }, state.error || "Loading the shop…"));
    return;
  }
  const catalog = state.catalog;
  chrome(catalog);
  let nodes = [];
  if (route.name === "home") nodes = renderHome(catalog);
  else if (route.name === "shop") nodes = renderShop(catalog, route);
  else if (route.name === "product") nodes = renderProduct(catalog, route);
  else if (route.name === "cart") nodes = renderCart(catalog);
  else if (route.name === "checkout") nodes = renderCheckout(catalog, route);
  else if (route.name === "order") nodes = await renderOrder(catalog, route);
  else if (route.name === "shipping") nodes = renderShipping(catalog);
  else if (route.name === "about") nodes = renderAbout(catalog);
  else nodes = renderMissing();
  app.replaceChildren(...nodes.filter(Boolean));
  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
}

document.addEventListener("click", (event) => {
  const remove = event.target.closest("[data-remove]");
  const qtyButton = event.target.closest("[data-qty]");
  if (remove || qtyButton) {
    const key = (remove || qtyButton).dataset.remove || (remove || qtyButton).dataset.key;
    const delta = qtyButton ? Number(qtyButton.dataset.qty) : 0;
    const lines = cart().flatMap((line) => {
      if (lineKey(line) !== key) return [line];
      if (remove) return [];
      const qty = line.qty + delta;
      return qty >= 1 && qty <= 4 ? [{ ...line, qty }] : [];
    });
    saveCart(lines);
    render();
    return;
  }
  const link = event.target.closest("a[href^='/']");
  if (!link || link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  navigate(link.getAttribute("href"));
});

window.addEventListener("popstate", () => { render(); });

async function boot() {
  try {
    state.catalog = await api("/api/catalog");
    state.error = "";
  } catch (error) {
    state.error = error.message;
  }
  render();
}

boot();
