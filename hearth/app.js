import {
  CITIES,
  DEMO_PASSWORD,
  addPhoto,
  blockPerson,
  createSeed,
  likePerson,
  logIn,
  makePlacePhoto,
  matchesFor,
  messagesBetween,
  profileForMember,
  removePhoto,
  reportPerson,
  sendMessage,
  signUp,
  updateProfile,
  visiblePeople,
} from "./logic.js";

const DB_KEY = "hearth-db-v1";
const SESSION_KEY = "hearth-session-v1";
const app = document.querySelector("#app");

let db = loadDb();
let meId = localStorage.getItem(SESSION_KEY);
let flash = "";
let keepFlash = false;
let joinError = "";
let joinDraft = {
  name: "",
  email: "",
  password: "",
  dob: "",
  city: "Brisbane",
  bio: "",
  confirm: false,
};
let loginError = "";
let photoIndex = 0;
let filter = "all";

function loadDb() {
  const raw = localStorage.getItem(DB_KEY);
  if (!raw) return createSeed();
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.users)) return createSeed();
    return parsed;
  } catch {
    return createSeed();
  }
}

function save() {
  localStorage.setItem(DB_KEY, JSON.stringify(db));
  if (meId) localStorage.setItem(SESSION_KEY, meId);
  else localStorage.removeItem(SESSION_KEY);
}

function me() {
  return db.users.find((user) => user.id === meId) || null;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function initials(name) {
  return name
    .split(" ")
    .map((part) => part[0] || "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function photoHtml(photo, name, className = "") {
  if (!photo) {
    return `<div class="placeholder ${className}">${esc(initials(name))}</div>`;
  }
  return `<img src="${esc(photo.src)}" alt="${esc(photo.label || `${name}, profile photo`)}" />`;
}

function formatTime(iso) {
  return new Intl.DateTimeFormat("en-AU", {
    timeZone: "Australia/Brisbane",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function route() {
  const parts = location.hash.replace(/^#/, "").split("/").filter(Boolean);
  return { name: parts[0] || "welcome", id: parts[1] || "" };
}

function go(hash) {
  keepFlash = true;
  if (location.hash === hash) {
    render();
    keepFlash = false;
  } else {
    location.hash = hash;
  }
}

function render() {
  const current = me();
  const { name, id } = route();
  if (!current && name !== "welcome" && name !== "join") {
    app.innerHTML = renderWelcome();
    return;
  }
  if (name === "join") app.innerHTML = renderJoin();
  else if (!current || name === "welcome") app.innerHTML = renderWelcome();
  else if (name === "person") app.innerHTML = shell(renderPerson(id));
  else if (name === "matches") app.innerHTML = shell(renderMatches());
  else if (name === "thread") app.innerHTML = shell(renderThread(id));
  else if (name === "me") app.innerHTML = shell(renderMe());
  else app.innerHTML = shell(renderDiscover());
  save();
}

function renderWelcome() {
  return `<section class="gate">
    <div class="intro">
      <p class="eyebrow">Australia · 18 and over</p>
      <h1>Hearth</h1>
      <p class="lede">A dating app for adults. Profiles, ordinary photos, and people in your city or a rough distance away.</p>
      <p class="fine">Profile photos are shown in full to other members. Distance is city to city, rounded, so a profile never pins a street address. This demo keeps accounts in this browser.</p>
    </div>
    <div class="panel">
      <h1>Log in</h1>
      ${loginError ? `<p class="error">${esc(loginError)}</p>` : ""}
      <form data-action="login">
        <label>Email <input name="email" type="email" autocomplete="username" required value="maya@hearth.test" /></label>
        <label>Password <input name="password" type="password" autocomplete="current-password" required value="${esc(DEMO_PASSWORD)}" /></label>
        <button class="primary" type="submit">Log in</button>
      </form>
      <div class="demos">
        <p>Demo profiles, password <strong>${esc(DEMO_PASSWORD)}</strong></p>
        <div class="stack">
          ${["Maya Chen", "Owen Blake", "Priya Nair", "Leo Santos", "Sofia Rossi"]
            .map((person) => {
              const email = `${person.split(" ")[0].toLowerCase()}@hearth.test`;
              return `<button class="secondary" type="button" data-action="demo" data-email="${email}">Continue as ${esc(person)}</button>`;
            })
            .join("")}
        </div>
      </div>
      <p><a class="textish" href="#/join">Create an account</a></p>
      <details>
        <summary>Demo tools</summary>
        <p class="fine">Reset puts the sample profiles back and logs you out.</p>
        <button class="ghost" type="button" data-action="reset">Reset demo data</button>
      </details>
    </div>
  </section>`;
}

function renderJoin() {
  return `<section class="gate">
    <div class="intro">
      <p class="eyebrow">Join Hearth</p>
      <h1>Adults only.</h1>
      <p class="lede">You need to be 18 or older. The date of birth is checked in this demo. It is not an identity document check.</p>
      <p><a class="textish" href="#/welcome">Back to log in</a></p>
    </div>
    <div class="panel">
      <h1>Create account</h1>
      ${joinError ? `<p class="error">${esc(joinError)}</p>` : ""}
      <form data-action="join">
        <label>Name <input name="name" required maxlength="40" value="${esc(joinDraft.name)}" /></label>
        <label>Email <input name="email" type="email" autocomplete="username" required value="${esc(joinDraft.email)}" /></label>
        <label>Password <input name="password" type="password" autocomplete="new-password" minlength="8" required value="${esc(joinDraft.password)}" /></label>
        <label>Date of birth <input name="dob" type="date" required value="${esc(joinDraft.dob)}" /></label>
        <label>City <select name="city">${Object.keys(CITIES)
          .map((city) => `<option ${city === joinDraft.city ? "selected" : ""}>${esc(city)}</option>`)
          .join("")}</select></label>
        <label>Bio <textarea name="bio" maxlength="280" required placeholder="A couple of sentences about you">${esc(joinDraft.bio)}</textarea></label>
        <label class="check"><input name="confirm" type="checkbox" required ${joinDraft.confirm ? "checked" : ""} /> <span>I am 18 or older.</span></label>
        <button class="primary" type="submit">Create account</button>
      </form>
    </div>
  </section>`;
}

function shell(body) {
  const current = me();
  const { name } = route();
  const item = (href, label, key) =>
    `<a href="${href}" ${name === key ? 'aria-current="page"' : ""}>${label}</a>`;
  return `<div class="shell">
    <header class="top">
      <a class="brand" href="#/discover">Hearth</a>
      <p class="who">${esc(current.name)} · ${esc(current.city)}</p>
    </header>
    ${flash ? `<p class="flash" role="status">${esc(flash)}</p>` : ""}
    <nav class="nav">
      ${item("#/discover", "Discover", "discover")}
      ${item("#/matches", "Matches", "matches")}
      ${item("#/me", "Profile", "me")}
    </nav>
    <main class="content">${body}</main>
  </div>`;
}

function renderDiscover() {
  const people = visiblePeople(db, meId, filter);
  const filters = [
    ["all", "Everyone"],
    ["city", "Same city"],
    ["near", "Within about 100 km"],
  ]
    .map(
      ([key, label]) =>
        `<button class="secondary" type="button" data-action="filter" data-filter="${key}" aria-pressed="${filter === key}">${label}</button>`,
    )
    .join("");
  const cards = people
    .map(
      (person) => `<a class="card" href="#/person/${esc(person.id)}">
        ${photoHtml(person.photos[0], person.name)}
        <div>
          <strong>${esc(person.name)}, ${esc(person.age)}</strong>
          <p class="meta">${esc(person.city)} · ${esc(person.distanceLabel)}</p>
          <p class="bio">${esc(person.bio)}</p>
        </div>
      </a>`,
    )
    .join("");
  return `<section>
    <p class="eyebrow">Discover</p>
    <div class="filters">${filters}</div>
    ${cards ? `<div class="cards">${cards}</div>` : `<p class="lede">No one in this range yet.</p>`}
  </section>`;
}

function renderPerson(id) {
  const person = profileForMember(db, meId, id);
  if (!person || person.id === meId) {
    return `<section class="person"><div class="copy"><h2>That profile is not available.</h2><p><a class="textish" href="#/discover">Back to discover</a></p></div></section>`;
  }
  const index = Math.min(photoIndex, Math.max(person.photos.length - 1, 0));
  const hero = person.photos[index];
  const thumbs = person.photos
    .map(
      (photo, i) =>
        `<button class="thumb" type="button" data-action="hero" data-index="${i}" aria-pressed="${i === index}" aria-label="Show photo ${i + 1}">${photoHtml(photo, person.name)}</button>`,
    )
    .join("");
  const likeLabel = person.matched ? "Matched" : person.liked ? "Liked" : `Like ${person.name}`;
  return `<article class="person">
    <div class="hero">
      ${photoHtml(hero, person.name)}
      ${person.photos.length > 1 ? `<div class="thumbs">${thumbs}</div>` : ""}
    </div>
    <div class="copy">
      <p class="eyebrow">${esc(person.distanceLabel)}</p>
      <h2>${esc(person.name)}, ${esc(person.age)}</h2>
      <p class="meta">${esc(person.city)} · ${esc(person.distanceLabel)}</p>
      <p class="bio">${esc(person.bio)}</p>
      <div class="row">
        ${
          person.matched
            ? `<a class="primary" href="#/thread/${esc(person.id)}">Message</a>`
            : `<button class="primary" type="button" data-action="like" data-id="${esc(person.id)}" ${person.liked ? "disabled" : ""}>${esc(likeLabel)}</button>`
        }
        <button class="ghost" type="button" data-action="block" data-id="${esc(person.id)}">Block</button>
      </div>
      <details>
        <summary>Report ${esc(person.name)}</summary>
        <form data-action="report" data-id="${esc(person.id)}">
          <label>Reason
            <select name="reason">
              <option>Harassment</option>
              <option>Fake profile</option>
              <option>Photo is not them</option>
              <option>They seem under 18</option>
              <option>Something else</option>
            </select>
          </label>
          <button class="secondary" type="submit">Submit report</button>
        </form>
      </details>
    </div>
  </article>`;
}

function renderMatches() {
  const matches = matchesFor(db, meId);
  if (!matches.length) {
    return `<section><p class="eyebrow">Matches</p><p class="lede">When you both like each other, the conversation shows up here.</p></section>`;
  }
  const items = matches
    .map(
      (person) => `<a href="#/thread/${esc(person.id)}">
        ${photoHtml(person.photos[0], person.name)}
        <span><strong>${esc(person.name)}</strong><span class="meta">${esc(person.lastText || "Say hello")}</span></span>
      </a>`,
    )
    .join("");
  return `<section><p class="eyebrow">Matches</p><div class="match-list">${items}</div></section>`;
}

function renderThread(id) {
  const person = profileForMember(db, meId, id);
  if (!person || !person.matched) {
    return `<section class="thread"><h2>Conversation unavailable.</h2><p><a class="textish" href="#/matches">Back to matches</a></p></section>`;
  }
  const bubbles = messagesBetween(db, meId, id)
    .map(
      (message) => `<div class="bubble ${message.fromId === meId ? "mine" : ""}">
        <span>${esc(message.text)}</span>
        <time datetime="${esc(message.at)}">${esc(formatTime(message.at))}</time>
      </div>`,
    )
    .join("");
  return `<section class="thread">
    <div class="split"><h2>${esc(person.name)}</h2><a class="textish" href="#/person/${esc(person.id)}">Profile</a></div>
    <div class="bubbles">${bubbles || `<p class="fine">Say hello.</p>`}</div>
    <form data-action="send" data-id="${esc(person.id)}">
      <label>Message <textarea name="text" maxlength="1000" required></textarea></label>
      <button class="primary" type="submit">Send</button>
    </form>
  </section>`;
}

function renderMe() {
  const user = profileForMember(db, meId, meId);
  const photos = user.photos
    .map(
      (photo) => `<figure>
        ${photoHtml(photo, user.name)}
        <figcaption><span>${esc(photo.label)}</span><button class="ghost" type="button" data-action="remove-photo" data-id="${esc(photo.id)}">Remove</button></figcaption>
      </figure>`,
    )
    .join("");
  return `<section class="me">
    <p class="eyebrow">Your profile · ${esc(user.age)}</p>
    <h2>${esc(user.name)}</h2>
    <p class="fine">These are ordinary profile photos. Other members see them in full on your profile. Hearth does not keep a hidden album.</p>
    <div class="photo-grid">${photos || `<p>No photo yet. Add one and it shows on your profile straight away.</p>`}</div>
    <div class="row">
      <button class="secondary" type="button" data-action="sample-photo">Add sample photo</button>
      <label class="secondary">Upload photo <input data-action="upload" type="file" accept="image/*" hidden /></label>
    </div>
    <form class="editor" data-action="save-profile">
      <label>Name <input name="name" maxlength="40" required value="${esc(user.name)}" /></label>
      <label>City <select name="city">${Object.keys(CITIES)
        .map((city) => `<option ${city === user.city ? "selected" : ""}>${esc(city)}</option>`)
        .join("")}</select></label>
      <label>Bio <textarea name="bio" maxlength="280" required>${esc(user.bio)}</textarea></label>
      <button class="primary" type="submit">Save profile</button>
    </form>
    <div class="row">
      <button class="ghost" type="button" data-action="logout">Log out</button>
    </div>
  </section>`;
}

app.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target || target.closest("form")) return;
  const action = target.dataset.action;
  if (action === "demo") {
    const result = logIn(db, target.dataset.email, DEMO_PASSWORD);
    if (!result.ok) {
      loginError = result.error;
      render();
      return;
    }
    meId = result.userId;
    loginError = "";
    go("#/discover");
  }
  if (action === "reset") {
    db = createSeed();
    meId = null;
    localStorage.removeItem(DB_KEY);
    localStorage.removeItem(SESSION_KEY);
    loginError = "";
    joinError = "";
    flash = "";
    go("#/welcome");
  }
  if (action === "logout") {
    meId = null;
    go("#/welcome");
  }
  if (action === "filter") {
    filter = target.dataset.filter;
    render();
  }
  if (action === "hero") {
    photoIndex = Number(target.dataset.index);
    render();
  }
  if (action === "like") {
    const result = likePerson(db, meId, target.dataset.id);
    flash = result.ok
      ? result.matched
        ? "You both liked each other. You can message now."
        : "Like saved."
      : result.error;
    render();
  }
  if (action === "block") {
    blockPerson(db, meId, target.dataset.id);
    flash = "Blocked. They are hidden from your discover list.";
    go("#/discover");
  }
  if (action === "sample-photo") {
    const result = addPhoto(db, meId, {
      src: makePlacePhoto("New photo", "#1f6b4a", "#e7c87a"),
      label: "Sample photo",
    });
    flash = result.ok ? "Photo added. Other members can see it in full." : result.error;
    render();
  }
  if (action === "remove-photo") {
    const result = removePhoto(db, meId, target.dataset.id);
    flash = result.ok ? "Photo removed." : result.error;
    render();
  }
});

app.addEventListener("change", async (event) => {
  const input = event.target;
  if (input.dataset.action !== "upload") return;
  const file = input.files && input.files[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    flash = "Choose an image file.";
    render();
    return;
  }
  if (file.size > 700_000) {
    flash = "That image is too large.";
    render();
    return;
  }
  const src = await readFile(file);
  const result = addPhoto(db, meId, { src, label: "Uploaded photo" });
  flash = result.ok ? "Photo added. Other members can see it in full." : result.error;
  render();
});

app.addEventListener("submit", (event) => {
  const form = event.target;
  const action = form.dataset.action;
  if (!action) return;
  event.preventDefault();
  const data = new FormData(form);
  if (action === "login") {
    const result = logIn(db, data.get("email"), data.get("password"));
    if (!result.ok) {
      loginError = result.error;
      render();
      return;
    }
    meId = result.userId;
    loginError = "";
    go("#/discover");
  }
  if (action === "join") {
    joinDraft = {
      name: String(data.get("name") || ""),
      email: String(data.get("email") || ""),
      password: String(data.get("password") || ""),
      dob: String(data.get("dob") || ""),
      city: String(data.get("city") || "Brisbane"),
      bio: String(data.get("bio") || ""),
      confirm: form.elements.confirm.checked,
    };
    if (!joinDraft.confirm) {
      joinError = "Confirm that you are 18 or older.";
      render();
      return;
    }
    const result = signUp(db, joinDraft, new Date());
    if (!result.ok) {
      joinError = result.error;
      render();
      return;
    }
    meId = result.userId;
    joinError = "";
    flash = "Account created.";
    go("#/me");
  }
  if (action === "save-profile") {
    const result = updateProfile(db, meId, {
      name: data.get("name"),
      city: data.get("city"),
      bio: data.get("bio"),
    });
    flash = result.ok ? "Profile saved." : result.error;
    render();
  }
  if (action === "send") {
    const result = sendMessage(db, meId, form.dataset.id, data.get("text"));
    flash = result.ok ? "" : result.error;
    render();
  }
  if (action === "report") {
    const result = reportPerson(db, meId, form.dataset.id, data.get("reason"));
    flash = result.ok
      ? "Report saved on this device. A live service would send it to a review team."
      : result.error;
    render();
  }
});

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

window.addEventListener("hashchange", () => {
  if (!keepFlash) flash = "";
  keepFlash = false;
  photoIndex = 0;
  if (route().name !== "join") joinError = "";
  render();
});

if (!location.hash) location.hash = "#/welcome";
render();
