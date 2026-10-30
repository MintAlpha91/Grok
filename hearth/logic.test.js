import assert from "node:assert/strict";
import test from "node:test";
import {
  addPhoto,
  ageOn,
  blockPerson,
  createSeed,
  distanceKm,
  distanceLabel,
  likePerson,
  logIn,
  makePortrait,
  profileForMember,
  sendMessage,
  signUp,
  visiblePeople,
} from "./logic.js";

const today = new Date(2026, 9, 30);

test("18th birthday can join and 17 cannot", () => {
  const db = createSeed();
  const before = db.users.length;
  const tooYoung = signUp(
    db,
    {
      name: "Alex Taylor",
      email: "alex@example.com",
      password: "correct-horse",
      dob: "2008-10-31",
      city: "Brisbane",
      bio: "This account should not be created.",
    },
    today,
  );
  assert.equal(tooYoung.ok, false);
  assert.equal(tooYoung.error, "You need to be 18 or older to join Hearth.");
  assert.equal(db.users.length, before);

  const oldEnough = signUp(
    db,
    {
      name: "Alex Taylor",
      email: "alex@example.com",
      password: "correct-horse",
      dob: "2008-10-30",
      city: "Brisbane",
      bio: "Just turned 18 and living in Brisbane.",
    },
    today,
  );
  assert.equal(oldEnough.ok, true);
  assert.equal(ageOn("2008-10-30", today), 18);
  assert.equal(ageOn("2008-10-31", today), 17);
});

test("profile photos are visible in full to other members", () => {
  const db = createSeed();
  const src = makePortrait("ZZ", "#112233", "#eeddcc");
  const added = addPhoto(db, "maya", { src, label: "New profile photo" });
  assert.equal(added.ok, true);
  const seen = profileForMember(db, "priya", "maya");
  assert.ok(seen.photos.some((photo) => photo.src === src));
  assert.equal(Object.hasOwn(seen, "privatePhotos"), false);
  const own = profileForMember(db, "maya", "maya");
  assert.deepEqual(
    own.photos.map((photo) => photo.src),
    seen.photos.map((photo) => photo.src),
  );
});

test("private and explicit albums are refused", () => {
  const db = createSeed();
  const src = makePortrait("ZZ", "#112233", "#eeddcc");
  const refused = addPhoto(db, "maya", { src, album: "private" });
  assert.equal(refused.ok, false);
  const explicit = addPhoto(db, "maya", { src, album: "explicit" });
  assert.equal(explicit.ok, false);
  assert.equal(profileForMember(db, "priya", "maya").photos.length, 2);
});

test("discovery uses city and approximate distance", () => {
  const db = createSeed();
  assert.equal(distanceLabel("Brisbane", "Brisbane"), "Same city");
  const coast = distanceKm("Brisbane", "Gold Coast");
  assert.ok(coast > 50 && coast < 90);
  assert.equal(distanceLabel("Brisbane", "Gold Coast"), "About 70 km away");
  const near = visiblePeople(db, "maya", "near").map((person) => person.id);
  assert.deepEqual(near.sort(), ["owen", "priya", "sofia"]);
  const city = visiblePeople(db, "maya", "city").map((person) => person.id);
  assert.deepEqual(city, ["priya"]);
  const sydney = visiblePeople(db, "maya", "all").find((person) => person.id === "leo");
  assert.match(sydney.distanceLabel, /^About \d+ km away$/);
  assert.ok(sydney.distanceKm > 600);
  assert.ok(sydney.photos[0].src.startsWith("data:image/"));
});

test("matching, messaging, and block", () => {
  const db = createSeed();
  assert.equal(likePerson(db, "priya", "maya").matched, true);
  const sent = sendMessage(db, "priya", "maya", "Coffee in West End?");
  assert.equal(sent.ok, true);
  const stranger = sendMessage(db, "priya", "leo", "Hello");
  assert.equal(stranger.ok, false);
  assert.equal(blockPerson(db, "maya", "leo").ok, true);
  assert.equal(profileForMember(db, "maya", "leo"), null);
  assert.equal(visiblePeople(db, "maya", "all").some((person) => person.id === "leo"), false);
});

test("demo login works and a wrong password does not", () => {
  const db = createSeed();
  assert.equal(logIn(db, "Maya@Hearth.Test", "hearth-demo").ok, true);
  assert.equal(logIn(db, "maya@hearth.test", "nope").ok, false);
});
