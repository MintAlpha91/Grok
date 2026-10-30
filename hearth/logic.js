/** Dating rules for Hearth, an 18+ Australian app. Profile photos are visible to members. */

export const MIN_AGE = 18;
export const DEMO_PASSWORD = "hearth-demo";

export const CITIES = {
  Brisbane: { lat: -27.4698, lng: 153.0251 },
  "Gold Coast": { lat: -28.0167, lng: 153.4 },
  "Sunshine Coast": { lat: -26.65, lng: 153.0667 },
  Sydney: { lat: -33.8688, lng: 151.2093 },
  Melbourne: { lat: -37.8136, lng: 144.9631 },
  Canberra: { lat: -35.2809, lng: 149.13 },
  Adelaide: { lat: -34.9285, lng: 138.6007 },
  Perth: { lat: -31.9523, lng: 115.8613 },
  Hobart: { lat: -42.8821, lng: 147.3272 },
  Darwin: { lat: -12.4634, lng: 130.8456 },
};

const CITY_NAMES = Object.keys(CITIES);

export function ageOn(dob, today) {
  if (typeof dob !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(dob)) return null;
  const [year, month, day] = dob.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }
  let age = today.getFullYear() - year;
  const todayMonth = today.getMonth() + 1;
  const todayDay = today.getDate();
  if (todayMonth < month || (todayMonth === month && todayDay < day)) age -= 1;
  return age;
}

export function makePortrait(initials, background, foreground) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000" viewBox="0 0 800 1000"><rect width="800" height="1000" fill="${background}"/><circle cx="400" cy="380" r="148" fill="${foreground}"/><ellipse cx="400" cy="860" rx="230" ry="180" fill="${foreground}"/><text x="400" y="412" text-anchor="middle" font-family="Georgia, serif" font-size="96" fill="${background}">${initials}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function makePlacePhoto(title, from, to) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000" viewBox="0 0 800 1000"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient></defs><rect width="800" height="1000" fill="url(#g)"/><circle cx="620" cy="180" r="70" fill="#fff6df" opacity="0.85"/><path d="M0 760 C160 680 240 820 400 760 C560 700 640 820 800 740 L800 1000 L0 1000 Z" fill="#1e3a2f" opacity="0.35"/><text x="64" y="880" font-family="Georgia, serif" font-size="54" fill="#fffaf3">${title}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function photo(id, src, label) {
  return { id, src, label };
}

export function createSeed() {
  return {
    users: [
      {
        id: "maya",
        email: "maya@hearth.test",
        password: DEMO_PASSWORD,
        name: "Maya Chen",
        dob: "1996-04-12",
        city: "Brisbane",
        bio: "Product designer in West End. I like river walks, late noodles, and someone who texts back.",
        photos: [
          photo("maya-1", makePortrait("MC", "#1f6b4a", "#e7f2ea"), "Maya at home"),
          photo("maya-2", makePlacePhoto("South Bank", "#f0b429", "#dd6b4d"), "South Bank"),
        ],
      },
      {
        id: "owen",
        email: "owen@hearth.test",
        password: DEMO_PASSWORD,
        name: "Owen Blake",
        dob: "1992-11-02",
        city: "Gold Coast",
        bio: "Chef in Burleigh. I am in Brisbane most weekends and I cook more than I should.",
        photos: [
          photo("owen-1", makePortrait("OB", "#8c3f2a", "#f6e4d4"), "Owen"),
          photo("owen-2", makePlacePhoto("Burleigh", "#2f6f8f", "#d7efe8"), "Burleigh"),
        ],
      },
      {
        id: "priya",
        email: "priya@hearth.test",
        password: DEMO_PASSWORD,
        name: "Priya Nair",
        dob: "1998-02-14",
        city: "Brisbane",
        bio: "Physiotherapist. Early swims, bad movie nights, and coffee that is stronger than necessary.",
        photos: [photo("priya-1", makePortrait("PN", "#243e73", "#e4e9f8"), "Priya")],
      },
      {
        id: "leo",
        email: "leo@hearth.test",
        password: DEMO_PASSWORD,
        name: "Leo Santos",
        dob: "1985-07-19",
        city: "Sydney",
        bio: "Architect in Surry Hills. I visit family in Queensland and I am better at galleries than small talk.",
        photos: [photo("leo-1", makePortrait("LS", "#3f3a33", "#f3eadf"), "Leo")],
      },
      {
        id: "sofia",
        email: "sofia@hearth.test",
        password: DEMO_PASSWORD,
        name: "Sofia Rossi",
        dob: "1995-09-01",
        city: "Sunshine Coast",
        bio: "Landscape gardener. Dirt under the nails, farmers markets, and a very patient dog.",
        photos: [photo("sofia-1", makePortrait("SR", "#3d6b45", "#e5f0d8"), "Sofia")],
      },
    ],
    likes: [
      { fromId: "maya", toId: "owen" },
      { fromId: "owen", toId: "maya" },
      { fromId: "maya", toId: "priya" },
      { fromId: "leo", toId: "maya" },
    ],
    messages: [
      {
        id: "msg-1",
        fromId: "owen",
        toId: "maya",
        text: "Want to get coffee when I am up in Brisbane this weekend?",
        at: "2026-10-28T01:15:00.000Z",
      },
      {
        id: "msg-2",
        fromId: "maya",
        toId: "owen",
        text: "Yes. Somewhere near South Bank works.",
        at: "2026-10-28T08:40:00.000Z",
      },
    ],
    blocks: [],
    reports: [],
  };
}

function fail(error) {
  return { ok: false, error };
}

function userById(db, id) {
  return db.users.find((user) => user.id === id) || null;
}

function userByEmail(db, email) {
  const normalised = String(email || "").trim().toLowerCase();
  return db.users.find((user) => user.email === normalised) || null;
}

export function isBlocked(db, a, b) {
  return db.blocks.some(
    (entry) =>
      (entry.blockerId === a && entry.blockedId === b) ||
      (entry.blockerId === b && entry.blockedId === a),
  );
}

export function signUp(db, input, today) {
  const name = String(input.name || "").trim();
  const email = String(input.email || "").trim().toLowerCase();
  const password = String(input.password || "");
  const dob = String(input.dob || "");
  const city = String(input.city || "");
  const bio = String(input.bio || "").trim();
  if (name.length < 2 || name.length > 40) return fail("Enter your name.");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return fail("Enter a valid email.");
  if (userByEmail(db, email)) return fail("That email is already registered.");
  if (password.length < 8) return fail("Use a password of at least 8 characters.");
  const age = ageOn(dob, today);
  if (age === null) return fail("Enter a real date of birth.");
  if (age < MIN_AGE) return fail("You need to be 18 or older to join Hearth.");
  if (age > 120) return fail("Enter a real date of birth.");
  if (!CITY_NAMES.includes(city)) return fail("Choose a city in Australia.");
  if (bio.length < 8 || bio.length > 280) return fail("Add a short bio.");
  const user = {
    id: crypto.randomUUID(),
    email,
    password,
    name,
    dob,
    city,
    bio,
    photos: [],
  };
  db.users.push(user);
  return { ok: true, userId: user.id };
}

export function logIn(db, email, password) {
  const user = userByEmail(db, email);
  if (!user || user.password !== String(password || "")) {
    return fail("Email or password does not match.");
  }
  return { ok: true, userId: user.id };
}

export function updateProfile(db, userId, input) {
  const user = userById(db, userId);
  if (!user) return fail("Profile not found.");
  const name = String(input.name || "").trim();
  const city = String(input.city || "");
  const bio = String(input.bio || "").trim();
  if (name.length < 2 || name.length > 40) return fail("Enter your name.");
  if (!CITY_NAMES.includes(city)) return fail("Choose a city in Australia.");
  if (bio.length < 8 || bio.length > 280) return fail("Add a short bio.");
  user.name = name;
  user.city = city;
  user.bio = bio;
  return { ok: true };
}

export function addPhoto(db, userId, photoInput) {
  const user = userById(db, userId);
  if (!user) return fail("Profile not found.");
  if (photoInput && photoInput.album && photoInput.album !== "profile") {
    return fail(
      "Profile photos are visible to other members. Hearth does not keep a private or explicit album.",
    );
  }
  const src = String(photoInput.src || "");
  if (!src.startsWith("data:image/")) return fail("Choose an image file.");
  if (src.length > 1_200_000) return fail("That image is too large.");
  if (user.photos.length >= 6) return fail("You can add up to 6 photos.");
  const label = String(photoInput.label || "Profile photo").slice(0, 80);
  const next = { id: crypto.randomUUID(), src, label };
  user.photos.push(next);
  return { ok: true, photoId: next.id };
}

export function removePhoto(db, userId, photoId) {
  const user = userById(db, userId);
  if (!user) return fail("Profile not found.");
  const before = user.photos.length;
  user.photos = user.photos.filter((item) => item.id !== photoId);
  if (user.photos.length === before) return fail("Photo not found.");
  return { ok: true };
}

function toRad(degrees) {
  return (degrees * Math.PI) / 180;
}

export function distanceKm(cityA, cityB) {
  const a = CITIES[cityA];
  const b = CITIES[cityB];
  if (!a || !b) return null;
  const earth = 6371;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * earth * Math.asin(Math.min(1, Math.sqrt(h)));
}

export function distanceLabel(cityA, cityB) {
  if (cityA === cityB) return "Same city";
  const km = distanceKm(cityA, cityB);
  if (km === null) return "Somewhere in Australia";
  const rounded = Math.max(10, Math.round(km / 10) * 10);
  return `About ${rounded} km away`;
}

export function isMatch(db, a, b) {
  const left = db.likes.some((like) => like.fromId === a && like.toId === b);
  const right = db.likes.some((like) => like.fromId === b && like.toId === a);
  return left && right;
}

function hasLike(db, fromId, toId) {
  return db.likes.some((like) => like.fromId === fromId && like.toId === toId);
}

function publicCard(db, viewer, person) {
  return {
    id: person.id,
    name: person.name,
    age: ageOn(person.dob, new Date()),
    city: person.city,
    bio: person.bio,
    distanceLabel: distanceLabel(viewer.city, person.city),
    distanceKm: distanceKm(viewer.city, person.city),
    photos: person.photos.map((item) => ({ ...item })),
    liked: hasLike(db, viewer.id, person.id),
    matched: isMatch(db, viewer.id, person.id),
  };
}

export function visiblePeople(db, userId, filter = "all") {
  const viewer = userById(db, userId);
  if (!viewer) return [];
  return db.users
    .filter((person) => person.id !== userId && !isBlocked(db, userId, person.id))
    .map((person) => publicCard(db, viewer, person))
    .filter((person) => {
      if (filter === "city") return person.city === viewer.city;
      if (filter === "near") return person.distanceKm !== null && person.distanceKm <= 100;
      return true;
    })
    .sort((a, b) => a.distanceKm - b.distanceKm || a.name.localeCompare(b.name));
}

/** The only photo read path. Members receive the same full profile photos. */
export function profileForMember(db, viewerId, ownerId) {
  const viewer = userById(db, viewerId);
  const owner = userById(db, ownerId);
  if (!viewer || !owner) return null;
  if (viewerId !== ownerId && isBlocked(db, viewerId, ownerId)) return null;
  return publicCard(db, viewerId === ownerId ? owner : viewer, owner);
}

export function likePerson(db, fromId, toId) {
  if (fromId === toId) return fail("You cannot like your own profile.");
  const from = userById(db, fromId);
  const to = userById(db, toId);
  if (!from || !to) return fail("Profile not found.");
  if (isBlocked(db, fromId, toId)) return fail("This profile is not available.");
  if (!hasLike(db, fromId, toId)) db.likes.push({ fromId, toId });
  return { ok: true, matched: isMatch(db, fromId, toId) };
}

export function sendMessage(db, fromId, toId, text) {
  const body = String(text || "").trim();
  if (!body) return fail("Write a message first.");
  if (body.length > 1000) return fail("That message is too long.");
  if (fromId === toId) return fail("You cannot message yourself.");
  if (!userById(db, fromId) || !userById(db, toId)) return fail("Profile not found.");
  if (isBlocked(db, fromId, toId)) return fail("This profile is not available.");
  if (!isMatch(db, fromId, toId)) return fail("You can message someone after you both like each other.");
  const message = {
    id: crypto.randomUUID(),
    fromId,
    toId,
    text: body,
    at: new Date().toISOString(),
  };
  db.messages.push(message);
  return { ok: true, messageId: message.id };
}

export function messagesBetween(db, a, b) {
  return db.messages
    .filter(
      (message) =>
        (message.fromId === a && message.toId === b) ||
        (message.fromId === b && message.toId === a),
    )
    .sort((left, right) => left.at.localeCompare(right.at));
}

export function matchesFor(db, userId) {
  const viewer = userById(db, userId);
  if (!viewer) return [];
  return db.users
    .filter((person) => person.id !== userId && isMatch(db, userId, person.id) && !isBlocked(db, userId, person.id))
    .map((person) => {
      const thread = messagesBetween(db, userId, person.id);
      const last = thread[thread.length - 1] || null;
      return {
        ...publicCard(db, viewer, person),
        lastText: last ? last.text : "",
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function blockPerson(db, blockerId, blockedId) {
  if (blockerId === blockedId) return fail("You cannot block yourself.");
  if (!userById(db, blockerId) || !userById(db, blockedId)) return fail("Profile not found.");
  if (!isBlocked(db, blockerId, blockedId)) {
    db.blocks.push({ blockerId, blockedId });
  }
  return { ok: true };
}

export function reportPerson(db, reporterId, targetId, reason) {
  const cleanReason = String(reason || "").trim();
  if (!cleanReason) return fail("Choose a reason.");
  if (reporterId === targetId) return fail("You cannot report yourself.");
  if (!userById(db, reporterId) || !userById(db, targetId)) return fail("Profile not found.");
  db.reports.push({
    id: crypto.randomUUID(),
    reporterId,
    targetId,
    reason: cleanReason.slice(0, 200),
    at: new Date().toISOString(),
  });
  return { ok: true };
}
