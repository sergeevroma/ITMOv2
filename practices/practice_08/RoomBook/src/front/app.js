const ui = {
  form: document.querySelector("#booking-form"),
  date: document.querySelector("#booking-date"),
  rooms: document.querySelector("#room-picker"),
  start: document.querySelector("#booking-start"),
  end: document.querySelector("#booking-end"),
  bookingHours: document.querySelector("#booking-hours"),
  configLoading: document.querySelector("#config-loading"),
  configError: document.querySelector("#config-error"),
  configRetry: document.querySelector("#config-retry"),
  schedule: document.querySelector("#schedule-panel"),
  scheduleDate: document.querySelector("#schedule-date"),
  scheduleHours: document.querySelector("#schedule-hours"),
  filter: document.querySelector("#schedule-room"),
  count: document.querySelector("#booking-count"),
  list: document.querySelector("#booking-list"),
  loading: document.querySelector("#schedule-loading"),
  empty: document.querySelector("#schedule-empty"),
  emptyTitle: document.querySelector("#empty-title"),
  emptyMessage: document.querySelector("#empty-message"),
  error: document.querySelector("#schedule-error"),
  retry: document.querySelector("#schedule-retry"),
  footer: document.querySelector("#schedule-footer"),
  hintTitle: document.querySelector("#schedule-hint-title"),
};

let rules = null;
let pendingSchedule = null;

async function fetchJson(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function cloneTemplate(id) {
  return document.querySelector(id).content.firstElementChild.cloneNode(true);
}

function renderRooms(rooms) {
  const choices = [];
  const filters = [new Option("Все комнаты", "")];
  for (const room of rooms) {
    const choice = cloneTemplate("#room-template");
    const radio = choice.querySelector("input");
    radio.value = room.id;
    radio.setAttribute("aria-label", room.name);
    choice.querySelector(".room-number").textContent = room.id;
    choice.querySelector(".room-capacity").textContent = `Мест: ${room.capacity}`;
    choice.querySelector(".room-equipment").textContent = room.equipment.join(", ");
    choices.push(choice);
    filters.push(new Option(room.name, room.id));
  }
  ui.rooms.replaceChildren(...choices);
  ui.filter.replaceChildren(...filters);
  ui.filter.disabled = false;
}

function toMinutes(value) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function formatTime(minutes) {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function renderTimeOptions() {
  const opening = toMinutes(rules.opens_at);
  const closing = toMinutes(rules.closes_at);
  for (const select of [ui.start, ui.end]) {
    const placeholder = new Option("Выберите", "", true, true);
    placeholder.disabled = true;
    select.replaceChildren(placeholder);
    select.disabled = false;
  }
  for (let minute = opening; minute <= closing; minute += rules.slot_minutes) {
    const time = formatTime(minute);
    if (minute < closing) ui.start.add(new Option(time, time));
    if (minute > opening) ui.end.add(new Option(time, time));
  }
  ui.bookingHours.textContent = `С ${rules.opens_at} до ${rules.closes_at}, интервал — ${rules.slot_minutes} минут.`;
  ui.scheduleHours.textContent = `${rules.opens_at}–${rules.closes_at}`;
}

function todayInTimezone(timezone) {
  const formatter = new Intl.DateTimeFormat("en", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
  });
  const parts = Object.fromEntries(formatter.formatToParts(new Date()).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function updateScheduleDate(day) {
  if (!day) {
    ui.scheduleDate.textContent = "Дата не выбрана";
    return;
  }
  const label = new Intl.DateTimeFormat("ru-RU", {
    timeZone: "UTC", weekday: "long", day: "numeric", month: "long",
  }).format(new Date(`${day}T12:00:00Z`));
  ui.scheduleDate.textContent = label[0].toUpperCase() + label.slice(1);
}

function showScheduleState(state) {
  ui.loading.hidden = state !== "loading";
  ui.error.hidden = state !== "error";
  ui.empty.hidden = state !== "empty" && state !== "date-required";
  ui.list.hidden = state !== "ready";
  ui.footer.hidden = state !== "ready" && state !== "empty";
  ui.schedule.setAttribute("aria-busy", String(state === "loading"));
  if (state !== "ready") {
    ui.list.replaceChildren();
    ui.count.textContent = state === "empty" ? "0 броней" : "—";
  }
  ui.emptyTitle.textContent = state === "date-required" ? "Выберите дату" : "Пока нет броней";
  ui.emptyMessage.textContent = state === "date-required"
    ? "Укажите дату в шапке, чтобы увидеть расписание."
    : "Для выбранной даты и фильтра бронирований нет.";
}

function createBookingCard(booking) {
  const card = cloneTemplate("#booking-template");
  const organizer = card.querySelector(".meeting-organizer");
  organizer.id = `meeting-${booking.id}`;
  card.setAttribute("aria-labelledby", organizer.id);
  card.querySelector(".room-badge").textContent = `Комната ${booking.room_id}`;
  for (const field of ["start", "end"]) {
    const time = card.querySelector(`[data-time="${field}"]`);
    time.dateTime = booking[field];
    time.textContent = booking[field];
  }
  organizer.textContent = booking.organizer;
  card.querySelector(".meeting-description").textContent = booking.title;
  card.querySelector("button").setAttribute(
    "aria-label", `Отменить бронь комнаты ${booking.room_id} на ${booking.start}`,
  );
  return card;
}

function renderSchedule(bookings) {
  ui.list.replaceChildren(...bookings.map(createBookingCard));
  showScheduleState(bookings.length ? "ready" : "empty");
  const word = { one: "бронь", few: "брони", many: "броней", other: "броней" };
  ui.count.textContent = `${bookings.length} ${word[new Intl.PluralRules("ru").select(bookings.length)]}`;
  if (bookings.length) {
    ui.hintTitle.textContent = ui.filter.value
      ? "В остальное время выбранная комната свободна"
      : "В остальное время комнаты свободны";
  } else {
    const subject = ui.filter.value ? "Выбранная комната свободна" : "Все комнаты свободны";
    ui.hintTitle.textContent = `${subject} с ${rules.opens_at} до ${rules.closes_at}`;
  }
}

async function loadSchedule() {
  if (!rules) return;
  pendingSchedule?.abort();
  const controller = new AbortController();
  pendingSchedule = controller;
  const day = ui.date.value;
  updateScheduleDate(day);
  if (!day || !ui.date.validity.valid) {
    showScheduleState("date-required");
    return;
  }
  showScheduleState("loading");
  const query = new URLSearchParams({ date: day });
  if (ui.filter.value) query.set("room_id", ui.filter.value);
  try {
    const bookings = await fetchJson(`/api/bookings?${query}`, controller.signal);
    if (!controller.signal.aborted) renderSchedule(bookings);
  } catch (error) {
    if (!controller.signal.aborted) showScheduleState("error");
  }
}

async function initialize() {
  ui.configLoading.hidden = false;
  ui.configError.hidden = true;
  ui.configRetry.disabled = true;
  try {
    const [rooms, bookingRules] = await Promise.all([
      fetchJson("/api/rooms"), fetchJson("/api/booking-rules"),
    ]);
    rules = bookingRules;
    renderRooms(rooms);
    renderTimeOptions();
    ui.date.value ||= todayInTimezone(rules.timezone);
    ui.date.disabled = false;
    ui.configLoading.hidden = true;
    await loadSchedule();
  } catch (error) {
    ui.configError.hidden = false;
  } finally {
    ui.configLoading.hidden = true;
    ui.configRetry.disabled = false;
  }
}

ui.date.addEventListener("change", loadSchedule);
ui.filter.addEventListener("change", loadSchedule);
ui.retry.addEventListener("click", loadSchedule);
ui.configRetry.addEventListener("click", initialize);
ui.form.addEventListener("submit", event => event.preventDefault());
initialize();
